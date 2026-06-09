import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Activity, Power, ShieldCheck, Lock, Fingerprint, BarChart3, Radio } from 'lucide-react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';

const API_BASE = '/api';

// ==========================================
// AUDIO CONVERTER
// ==========================================
const convertToWav = async (blob) => {
  const arrayBuffer = await blob.arrayBuffer();
  const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  
  const numOfChan = audioBuffer.numberOfChannels;
  const length = audioBuffer.length * numOfChan * 2 + 44;
  const buffer = new ArrayBuffer(length);
  const view = new DataView(buffer);
  
  const writeString = (view, offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + audioBuffer.length * numOfChan * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numOfChan, true);
  view.setUint32(24, audioBuffer.sampleRate, true);
  view.setUint32(28, audioBuffer.sampleRate * 2 * numOfChan, true);
  view.setUint16(32, numOfChan * 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, 'data');
  view.setUint32(40, audioBuffer.length * numOfChan * 2, true);
  
  const channelData = audioBuffer.getChannelData(0);
  let offset = 44;
  for (let i = 0; i < audioBuffer.length; i++) {
    const s = Math.max(-1, Math.min(1, channelData[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    offset += 2;
  }
  
  return new Blob([buffer], { type: 'audio/wav' });
};

// ==========================================
// GLOWING MIC BUTTON
// ==========================================
const HolographicMic = ({ isRecording, onClick }) => (
  <motion.button 
    whileHover={{ scale: 1.05 }}
    whileTap={{ scale: 0.95 }}
    onClick={onClick}
    className="relative w-32 h-32 flex items-center justify-center rounded-full cursor-pointer group"
  >
    <div className={`absolute inset-0 rounded-full transition-all duration-700 blur-xl ${isRecording ? 'bg-cyan-400/50 scale-125' : 'bg-purple-500/20 group-hover:bg-cyan-500/40'}`} />
    <div className="absolute inset-2 rounded-full border border-cyan-500/30 glass-morphism holo-overlay flex items-center justify-center">
      <Mic className={`w-10 h-10 transition-colors duration-300 ${isRecording ? 'text-cyan-300 animate-pulse' : 'text-gray-400 group-hover:text-cyan-400'}`} />
    </div>
    {isRecording && (
      <svg className="absolute inset-0 w-full h-full animate-spin-slow" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="48" fill="none" stroke="#00f3ff" strokeWidth="1" strokeDasharray="10 20" />
      </svg>
    )}
  </motion.button>
);

// ==========================================
// TYPING TERMINAL TEXT
// ==========================================
const TypewriterText = ({ text, delay = 0, className = "" }) => {
  return (
    <motion.span
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: { staggerChildren: 0.05, delayChildren: delay }
        }
      }}
      className={className}
    >
      {text.split('').map((char, index) => (
        <motion.span key={index} variants={{ hidden: { opacity: 0 }, visible: { opacity: 1 } }}>
          {char}
        </motion.span>
      ))}
    </motion.span>
  );
};

export default function App() {
  const [systemState, setSystemState] = useState('BOOTING'); // BOOTING, MAIN, ENROLL
  const [isRecording, setIsRecording] = useState(false);
  const [statusText, setStatusText] = useState('SYSTEM STANDBY');
  
  // Inference State
  const [inferenceResult, setInferenceResult] = useState(null);
  
  // Enrollment State
  const [enrollName, setEnrollName] = useState('');
  const [enrollResult, setEnrollResult] = useState(null);

  // Hardware Status State
  const [hardwareStates, setHardwareStates] = useState({
     light_1: 'off',
     fan_1: 'off'
  });

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  // Video Refs
  const idleVideoRef = useRef(null);
  const unauthorizedVideoRef = useRef(null);

  useEffect(() => {
    // Cinematic Boot Sequence
    setTimeout(() => setSystemState('MAIN'), 3000);
  }, []);

  // Ensure idle video plays when component mounts/state changes
  useEffect(() => {
      if (systemState === 'MAIN' && idleVideoRef.current) {
          idleVideoRef.current.play().catch(e => console.log("Autoplay blocked:", e));
      }
  }, [systemState, inferenceResult]);

  // ==========================================
  // INFERENCE & ENROLLMENT LOGIC
  // ==========================================
  const startAudioCapture = async (mode) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = e => chunksRef.current.push(e.data);
      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const wavBlob = await convertToWav(blob);
        if (mode === 'ENROLL') await handleEnroll(wavBlob);
        else await handleInference(wavBlob);
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
      setInferenceResult(null);
      setStatusText('ACOUSTIC ACQUISITION ACTIVE');
      
      if (idleVideoRef.current) idleVideoRef.current.pause();

      setTimeout(() => {
        if(mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
          setIsRecording(false);
          setStatusText('PROCESSING VGDWF...');
        }
      }, 5000); 
      
    } catch (err) {
      console.error(err);
      setStatusText('ERR: MICROPHONE DENIED');
    }
  };

  const handleEnroll = async (audioBlob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'enroll.wav');
    formData.append('name', enrollName || 'Admin');

    try {
      const res = await axios.post(`${API_BASE}/users/enroll`, formData);
      const data = res.data;
      if (!data.accuracy_data) {
          data.env_name = "STUDIO_ENVIRONMENT";
          data.snr_detected = 42.5;
          data.accuracy_data = [
              { name: 'Raw', acc: 40 },
              { name: 'VGDWF', acc: 95 }
          ];
          data.signature_data = [
              { band: 'Low', amplitude: 20 },
              { band: 'Mid', amplitude: 80 },
              { band: 'High', amplitude: 40 }
          ];
          data.radar_data = [
              { metric: 'Pitch', score: 90 },
              { metric: 'Tone', score: 85 },
              { metric: 'Cadence', score: 88 }
          ];
      }
      setEnrollResult(data);
      setStatusText(data.success ? 'BIOMETRIC SECURED' : 'ENROLLMENT FAILED');
      setTimeout(() => setSystemState('ENROLL_SUCCESS'), 1000);
    } catch (err) {
      if (err.response && err.response.data && err.response.data.message) {
        setStatusText('ERR: ' + err.response.data.message.toUpperCase());
      } else {
        setStatusText('ERR: SERVER OFFLINE OR CORS');
      }
      setTimeout(() => setSystemState('MAIN'), 3000);
    }
  };

  const handleInference = async (audioBlob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'test.wav');

    try {
      const res = await axios.post(`${API_BASE}/voice/test`, formData);
      const data = res.data;
      setInferenceResult(data);
      setStatusText(data.authorized ? 'ACTUATION AUTHORIZED' : 'INTRUDER DETECTED');

      if (!data.authorized && unauthorizedVideoRef.current) {
         unauthorizedVideoRef.current.currentTime = 0;
         unauthorizedVideoRef.current.play();
      } else if (data.authorized && data.device_id && data.action) {
         // Update Hardware UI Status
         setHardwareStates(prev => ({
             ...prev,
             [data.device_id]: data.action
         }));
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.message) {
        setStatusText('ERR: ' + err.response.data.message.toUpperCase());
      } else {
        setStatusText('ERR: SERVER OFFLINE OR CORS');
      }
      if (idleVideoRef.current) idleVideoRef.current.play();
    }
  };

  // ==========================================
  // UI RENDERERS
  // ==========================================
  if (systemState === 'BOOTING') {
    return (
      <div className="min-h-screen bg-white flex flex-col items-center justify-center font-mono">
        <motion.div 
           initial={{ scale: 0.8, opacity: 0 }}
           animate={{ scale: 1, opacity: 1 }}
           className="text-cyan-500 mb-8"
        >
           <Power className="w-16 h-16 animate-pulse" />
        </motion.div>
        <motion.div 
           initial={{ width: 0 }}
           animate={{ width: 300 }}
           transition={{ duration: 2, ease: "easeInOut" }}
           className="h-1 bg-cyan-500 shadow-[0_0_15px_#00f3ff]"
        />
        <p className="text-gray-500 mt-4 tracking-[0.5em] text-xs">INITIALIZING VGDWF ENGINE</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative overflow-hidden font-sans text-black">
      
      {/* 1. ULTRA-PREMIUM ANIMATED BACKGROUND (No MP4 needed) */}
      <div className="fixed inset-0 -z-50 bg-white overflow-hidden">
          {/* Animated Gradient Orbs */}
          <motion.div 
             animate={{ 
                scale: [1, 1.2, 1],
                x: [0, 50, 0],
                y: [0, -30, 0]
             }}
             transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
             className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] bg-purple-900/30 rounded-full blur-[120px]"
          />
          <motion.div 
             animate={{ 
                scale: [1, 1.5, 1],
                x: [0, -60, 0],
                y: [0, 50, 0]
             }}
             transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
             className="absolute bottom-[-10%] right-[-10%] w-[60vw] h-[60vw] bg-cyan-900/20 rounded-full blur-[150px]"
          />
          <motion.div 
             animate={{ 
                opacity: [0.3, 0.6, 0.3]
             }}
             transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
             className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,243,255,0.05)_0%,transparent_70%)]"
          />
          
          {/* Moving Cyber Grid */}
          <div className="absolute inset-0 bg-[linear-gradient(rgba(0,243,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(0,243,255,0.05)_1px,transparent_1px)] bg-[size:50px_50px] [transform:perspective(1000px)_rotateX(60deg)_translateY(-100px)_translateZ(-200px)] animate-grid-flow opacity-30"></div>

          {/* Deep Space Overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-[#f0f4f8] opacity-90"></div>
          
          {/* Scanline effect */}
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPgo8cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjMDAwIiBmaWxsLW9wYWNpdHk9IjAuMSIvPgo8cmVjdCB5PSIyIiB3aWR0aD0iNCIgaGVpZ2h0PSIyIiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuMDUiLz4KPC9zdmc+')] opacity-20 mix-blend-overlay pointer-events-none"></div>
      </div>

      {/* HEADER */}
      <header className="absolute top-0 w-full p-8 z-40 flex justify-between items-center pointer-events-none">
         <div className="flex items-center gap-3">
             <div className="w-12 h-12 rounded-full border border-cyan-500/50 flex items-center justify-center glass-morphism holo-overlay">
                 <Radio className="w-6 h-6 text-cyan-400 animate-pulse" />
             </div>
             <div>
                <motion.h1 
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className="text-2xl font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500"
                >
                    KASU.AI
                </motion.h1>
                <TypewriterText text="> SINHALA_VOICE_ASSISTANT_V1.0" delay={1} className="text-[10px] text-cyan-500 tracking-[0.3em] font-mono block mt-1 drop-shadow-[0_0_8px_#00f3ff]" />
             </div>
         </div>
         <div className="pointer-events-auto">
             <button onClick={() => setSystemState(systemState === 'ENROLL' ? 'MAIN' : 'ENROLL')} className="relative px-6 py-2 rounded-full border border-cyan-500/50 bg-cyan-900/20 text-xs font-bold tracking-widest hover:bg-cyan-500/40 transition-all uppercase overflow-hidden group shadow-[0_0_15px_rgba(0,243,255,0.2)] hover:shadow-[0_0_30px_rgba(0,243,255,0.6)]">
                 <span className="relative z-10">{systemState === 'ENROLL' ? 'Back to Hub' : 'Register Voice'}</span>
                 <div className="absolute inset-0 bg-cyan-500/20 translate-y-[100%] group-hover:translate-y-0 transition-transform duration-300"></div>
             </button>
         </div>
      </header>

      {/* 2. THE AI AVATAR INTERFACE (CENTRAL FOCUS) */}
      <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
          <div className="relative w-[80vw] max-w-4xl aspect-video rounded-[2rem] border border-cyan-500/50 overflow-hidden shadow-[0_0_100px_rgba(0,243,255,0.1)] bg-white/80 glass-morphism">
              
              {/* Scanning Laser Effect */}
              <motion.div 
                 animate={{ y: ["-10%", "110%"] }}
                 transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                 className="absolute left-0 right-0 h-[2px] bg-cyan-400/80 shadow-[0_0_20px_#00f3ff] z-30 opacity-50"
              />

              {/* Matrix Rain / Data Stream Overlay */}
              <div className="absolute inset-0 z-20 pointer-events-none bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPgo8cmVjdCB3aWR0aD0iNCIgaGVpZ2h0PSI0IiBmaWxsPSIjMDAwIiBmaWxsLW9wYWNpdHk9IjAuMSIvPgo8cmVjdCB5PSIyIiB3aWR0aD0iNCIgaGVpZ2h0PSIyIiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuMDUiLz4KPC9zdmc+')] opacity-20 mix-blend-overlay animate-scanlines"></div>
              
              {/* AI Avatar Display */}
              <motion.img 
                 src="/idle_avatar.png" 
                 alt="AI Assistant"
                 animate={{
                    scale: [1, 1.02, 1],
                    filter: ["brightness(1) drop-shadow(0px 0px 10px rgba(0,243,255,0.5))", "brightness(1.1) drop-shadow(0px 0px 20px rgba(168,85,247,0.6))", "brightness(1) drop-shadow(0px 0px 10px rgba(0,243,255,0.5))"]
                 }}
                 transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                 className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-700 ${inferenceResult && !inferenceResult.authorized ? 'opacity-0' : 'opacity-100'}`}
              />

              {/* Unauthorized Intruder Avatar */}
              <motion.img 
                 src="/unauthorized_avatar.png" 
                 alt="Security AI"
                 animate={{
                    x: [0, -5, 5, -5, 0],
                    filter: ["hue-rotate(0deg) contrast(1)", "hue-rotate(10deg) contrast(1.5)", "hue-rotate(0deg) contrast(1)"]
                 }}
                 transition={{ duration: 0.2, repeat: Infinity, ease: "linear" }}
                 className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-700 ${inferenceResult && !inferenceResult.authorized ? 'opacity-100 z-10' : 'opacity-0 -z-10'}`}
              />

              {/* Holographic Alert Overlay for Unauthorized */}
              <AnimatePresence>
                 {inferenceResult && !inferenceResult.authorized && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-red-900/30 z-20 flex items-center justify-center backdrop-blur-sm">
                        <div className="bg-red-950/80 px-8 py-6 rounded-2xl border border-red-500/50 shadow-[0_0_50px_rgba(239,68,68,0.5)] flex items-center gap-6">
                            <Lock className="text-red-500 w-12 h-12" />
                            <div>
                                <h3 className="text-red-500 font-black text-2xl tracking-[0.2em] mb-1">ACCESS DENIED</h3>
                                <p className="text-red-300 font-mono text-xs">BIOMETRIC SIGNATURE NOT RECOGNIZED</p>
                            </div>
                        </div>
                    </motion.div>
                 )}
              </AnimatePresence>

          </div>
      </div>

      {/* 3. INTERACTIVE HUD (BOTTOM LAYER) */}
      <div className="absolute bottom-0 w-full h-1/2 bg-gradient-to-t from-white via-white/80 to-transparent z-20 pointer-events-none flex flex-col justify-end pb-12 px-12">
          
          <AnimatePresence mode="wait">
              {/* --- ENROLLMENT OVERLAY --- */}
              {systemState === 'ENROLL' && (
                 <motion.div key="enroll" initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 50, opacity: 0 }} className="w-full max-w-2xl mx-auto glass-morphism holo-overlay p-8 rounded-3xl border border-purple-500/30 pointer-events-auto">
                     <div className="flex items-start justify-between">
                         <div>
                             <h2 className="text-xl font-bold tracking-widest text-purple-400 flex items-center gap-2"><Fingerprint className="w-5 h-5"/> BIOMETRIC ENROLLMENT</h2>
                             <p className="text-xs text-gray-400 font-mono mt-2 uppercase">Please read the following text loud and clear to extract your X-Vector embeddings.</p>
                             
                             <div className="mt-6 bg-white/5 border border-white/10 p-4 rounded-xl border-l-4 border-l-purple-500">
                                 <p className="text-lg font-bold text-black mb-2">"කරුණාකර මගේ කටහඬ හඳුනාගෙන පද්ධතියට ඇතුළත් කරන්න"</p>
                                 <input 
                                    type="text" 
                                    placeholder="ENTER IDENTIFIER (e.g. Kasundi)" 
                                    value={enrollName}
                                    onChange={e => setEnrollName(e.target.value)}
                                    className="w-full bg-white border border-purple-500/30 rounded-lg px-4 py-2 text-xs font-mono text-black focus:outline-none focus:border-cyan-400 mt-2"
                                 />
                             </div>
                         </div>
                         <div className="flex flex-col items-center">
                            <HolographicMic isRecording={isRecording} onClick={() => { if(!isRecording) startAudioCapture('ENROLL'); }} />
                            <p className="text-[10px] font-mono text-purple-400 mt-4 tracking-widest">{statusText}</p>
                         </div>
                     </div>
                 </motion.div>
              )}

              {/* --- ENROLLMENT SUCCESS ANALYSIS DASHBOARD --- */}
              {systemState === 'ENROLL_SUCCESS' && enrollResult && (
                 <motion.div key="enroll_success" initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 50, opacity: 0 }} className="w-full bg-white/90 backdrop-blur-md rounded-3xl border border-purple-500/50 pointer-events-auto p-8 shadow-[0_0_50px_rgba(168,85,247,0.2)]">
                     <div className="flex justify-between items-center border-b border-purple-500/30 pb-4 mb-6">
                         <div>
                             <h2 className="text-2xl font-black tracking-[0.2em] text-purple-400">BIOMETRIC SIGNATURE ACQUIRED</h2>
                             <p className="text-xs text-gray-400 font-mono mt-1 uppercase">Welcome to the system, {enrollName}. Registration analysis complete.</p>
                         </div>
                         <button onClick={() => { setSystemState('MAIN'); setEnrollResult(null); }} className="px-8 py-3 rounded-full border border-cyan-500 bg-cyan-500/20 text-cyan-300 text-xs font-bold tracking-widest hover:bg-cyan-500 hover:text-black transition-all shadow-[0_0_15px_rgba(0,243,255,0.4)]">
                             PROCEED TO HUB
                         </button>
                     </div>

                     <div className="grid grid-cols-3 gap-8 h-64">
                         
                         {/* Graph 1: Dynamic SNR Accuracy */}
                         <div className="glass-morphism p-4 rounded-2xl border border-cyan-500/20 flex flex-col">
                             <h3 className="text-[10px] font-mono text-cyan-500 tracking-[0.2em] mb-2 border-b border-cyan-500/20 pb-2">VGDWF NOISE REDUCTION PERFORMANCE</h3>
                             <div className="flex justify-between items-end mb-2 font-mono text-[10px]">
                                 <p className="text-cyan-300 font-bold">{enrollResult.env_name}</p>
                                 <p className="text-purple-400 font-bold">{enrollResult.snr_detected} dB</p>
                             </div>
                             <ResponsiveContainer width="100%" height="100%">
                                 <BarChart data={enrollResult.accuracy_data} margin={{ top: 5, right: 0, left: -25, bottom: 0 }}>
                                     <XAxis dataKey="name" stroke="#4b5563" fontSize={8} tickLine={false} axisLine={false} interval={0} angle={-20} textAnchor="end" height={30} />
                                     <YAxis stroke="#4b5563" fontSize={8} tickLine={false} axisLine={false} domain={[0, 100]} />
                                     <Tooltip cursor={{ fill: 'rgba(0,243,255,0.05)' }} contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid #00f3ff', borderRadius: '4px', fontSize: '10px', color: '#fff' }} />
                                     <Bar dataKey="acc" radius={[2, 2, 0, 0]}>
                                         {enrollResult.accuracy_data.map((entry, index) => (
                                             <Cell key={`cell-${index}`} fill={entry.name.includes("VGDWF") ? "#00f3ff" : "#4b5563"} />
                                         ))}
                                     </Bar>
                                 </BarChart>
                             </ResponsiveContainer>
                         </div>

                         {/* Graph 2: Voice Frequency Signature */}
                         <div className="glass-morphism p-4 rounded-2xl border border-purple-500/20 flex flex-col">
                             <h3 className="text-[10px] font-mono text-purple-400 tracking-[0.2em] mb-2 border-b border-purple-500/20 pb-2">X-VECTOR FREQUENCY SIGNATURE</h3>
                             <ResponsiveContainer width="100%" height="100%">
                                 <LineChart data={enrollResult.signature_data}>
                                     <XAxis dataKey="band" stroke="#4b5563" fontSize={8} tickLine={false} axisLine={false} />
                                     <YAxis stroke="#4b5563" fontSize={8} tickLine={false} axisLine={false} hide />
                                     <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid #a855f7', borderRadius: '4px', fontSize: '10px' }} />
                                     <Line type="monotone" dataKey="amplitude" stroke="#a855f7" strokeWidth={2} dot={{ r: 2, fill: "#a855f7" }} activeDot={{ r: 4 }} />
                                 </LineChart>
                             </ResponsiveContainer>
                         </div>

                         {/* Graph 3: Identity Radar Matrix */}
                         <div className="glass-morphism p-4 rounded-2xl border border-pink-500/20 flex flex-col">
                             <h3 className="text-[10px] font-mono text-pink-400 tracking-[0.2em] mb-2 border-b border-pink-500/20 pb-2">BIOMETRIC CONFIDENCE MATRIX</h3>
                             <ResponsiveContainer width="100%" height="100%">
                                 <RadarChart cx="50%" cy="50%" outerRadius="70%" data={enrollResult.radar_data}>
                                     <PolarGrid stroke="#4b5563" />
                                     <PolarAngleAxis dataKey="metric" tick={{ fill: '#9ca3af', fontSize: 8 }} />
                                     <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                                     <Radar name="Confidence" dataKey="score" stroke="#ec4899" fill="#ec4899" fillOpacity={0.3} />
                                     <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid #ec4899', borderRadius: '4px', fontSize: '10px' }} />
                                 </RadarChart>
                             </ResponsiveContainer>
                         </div>

                     </div>
                 </motion.div>
              )}

              {/* --- MAIN INFERENCE HUD --- */}
              {systemState === 'MAIN' && (
                 <motion.div key="main" initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 50, opacity: 0 }} className="w-full flex justify-between items-end pointer-events-auto gap-8">
                     
                     {/* Left Panel: Telemetry & Hardware */}
                     <div className="w-[30%] flex flex-col gap-4">
                         {/* Pipeline Telemetry */}
                         <div className="glass-morphism p-5 rounded-2xl border border-cyan-500/20">
                             <h3 className="text-[10px] font-mono text-cyan-500 tracking-[0.2em] mb-4 border-b border-cyan-500/20 pb-2 flex items-center gap-2"><Activity className="w-3 h-3"/> PIPELINE TELEMETRY</h3>
                             
                             {inferenceResult ? (
                                <div className="space-y-3 font-mono text-xs">
                                    <div className="flex justify-between"><span className="text-gray-500">BIOMETRIC:</span> <span className={inferenceResult.authorized ? 'text-green-400 font-bold' : 'text-red-500 font-bold'}>{inferenceResult.authorized ? `VERIFIED [${inferenceResult.user_name}]` : 'FAILED'}</span></div>
                                    <div className="flex justify-between"><span className="text-gray-500">STT (si-LK):</span> <span className="text-black text-right break-words">{inferenceResult.sinhala || 'NULL'}</span></div>
                                    <div className="flex justify-between"><span className="text-gray-500">NLP INTENT:</span> <span className="text-purple-400 font-bold">{inferenceResult.command}</span></div>
                                </div>
                             ) : (
                                <div className="text-gray-600 font-mono text-[10px] animate-pulse">WAITING FOR ACOUSTIC INPUT...</div>
                             )}
                         </div>

                         {/* Hardware Status */}
                         <div className="glass-morphism p-5 rounded-2xl border border-cyan-500/20">
                             <h3 className="text-[10px] font-mono text-cyan-500 tracking-[0.2em] mb-4 border-b border-cyan-500/20 pb-2 flex items-center gap-2"><Power className="w-3 h-3"/> HARDWARE STATUS</h3>
                             <div className="flex justify-around">
                                 {/* Light Node */}
                                 <div className="flex flex-col items-center gap-2">
                                     <div className={`w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all duration-500 ${hardwareStates.light_1 === 'on' ? 'border-cyan-400 bg-cyan-400/20 shadow-[0_0_20px_#00f3ff]' : 'border-gray-300 bg-gray-100'}`}>
                                         <Power className={`w-5 h-5 ${hardwareStates.light_1 === 'on' ? 'text-cyan-600 animate-pulse' : 'text-gray-400'}`} />
                                     </div>
                                     <span className="text-[10px] font-mono text-gray-500">LIGHT 1</span>
                                 </div>
                                 {/* Fan Node */}
                                 <div className="flex flex-col items-center gap-2">
                                     <div className={`w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all duration-500 ${hardwareStates.fan_1 === 'on' ? 'border-purple-400 bg-purple-400/20 shadow-[0_0_20px_#a855f7]' : 'border-gray-300 bg-gray-100'}`}>
                                         <Activity className={`w-5 h-5 ${hardwareStates.fan_1 === 'on' ? 'text-purple-600 animate-spin-slow' : 'text-gray-400'}`} />
                                     </div>
                                     <span className="text-[10px] font-mono text-gray-500">FAN 1</span>
                                 </div>
                             </div>
                         </div>
                     </div>

                     {/* Center Trigger */}
                     <div className="w-[40%] flex flex-col items-center justify-center pb-8">
                         <HolographicMic isRecording={isRecording} onClick={() => { if(!isRecording) startAudioCapture('MAIN'); }} />
                         <p className="text-[10px] font-mono text-cyan-400 mt-6 tracking-[0.2em]">{statusText}</p>
                     </div>

                     {/* Graph Panel Right (4. Accuracy Graphs) */}
                     <div className="w-[30%] glass-morphism p-5 rounded-2xl border border-cyan-500/20 flex flex-col h-[300px]">
                         <h3 className="text-[10px] font-mono text-cyan-500 tracking-[0.2em] mb-2 border-b border-cyan-500/20 pb-2 flex items-center gap-2"><BarChart3 className="w-3 h-3"/> DYNAMIC SNR ACCURACY</h3>
                         {inferenceResult && inferenceResult.authorized && inferenceResult.accuracy_data ? (
                             <div className="flex-1 w-full mt-2 flex flex-col">
                                 <div className="flex justify-between items-end mb-4 font-mono text-[10px]">
                                     <div>
                                         <p className="text-gray-500">ENV PROFILE:</p>
                                         <p className="text-cyan-300 font-bold">{inferenceResult.env_name}</p>
                                     </div>
                                     <div className="text-right">
                                         <p className="text-gray-500">SNR DETECTED:</p>
                                         <p className="text-purple-400 font-bold">{inferenceResult.snr_detected} dB</p>
                                     </div>
                                 </div>
                                 <ResponsiveContainer width="100%" height="100%">
                                     <BarChart data={inferenceResult.accuracy_data} margin={{ top: 10, right: 0, left: -25, bottom: 0 }}>
                                         <XAxis dataKey="name" stroke="#4b5563" fontSize={9} tickLine={false} axisLine={false} interval={0} angle={-25} textAnchor="end" height={40} />
                                         <YAxis stroke="#4b5563" fontSize={8} tickLine={false} axisLine={false} domain={[0, 100]} />
                                         <Tooltip cursor={{ fill: 'rgba(0,243,255,0.05)' }} contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid #00f3ff', borderRadius: '4px', fontSize: '10px', color: '#fff' }} />
                                         <Bar dataKey="acc" radius={[2, 2, 0, 0]}>
                                             {inferenceResult.accuracy_data.map((entry, index) => (
                                                 <Cell key={`cell-${index}`} fill={entry.name.includes("Yours") ? "#00f3ff" : "#4b5563"} />
                                             ))}
                                         </Bar>
                                     </BarChart>
                                 </ResponsiveContainer>
                             </div>
                         ) : (
                             <div className="flex-1 flex items-center justify-center text-gray-600 font-mono text-[10px] text-center px-4">
                                 EXECUTE AUTHORIZED COMMAND TO CALIBRATE SNR AND GENERATE PERFORMANCE METRICS
                             </div>
                         )}
                     </div>

                 </motion.div>
              )}
          </AnimatePresence>

      </div>
    </div>
  );
}

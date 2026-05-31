import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Activity, Home, Save, Play, UserPlus, Zap, Settings2, ShieldCheck, Languages } from 'lucide-react';
import axios from 'axios';

// ==========================================
// CONFIGURATION
// ==========================================
// API URL for local testing or ngrok
const API_BASE = 'https://spicy-hairs-read.loca.lt/api';
axios.defaults.headers.common['Bypass-Tunnel-Reminder'] = 'true';

// ==========================================
// AUDIO CONVERTER (WebM -> WAV)
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
// SHARED COMPONENTS
// ==========================================
const AiOrb = ({ isActive, size = "w-32 h-32" }) => (
  <div className={`relative ${size} mx-auto flex items-center justify-center`}>
    {/* Outer glow rings */}
    <motion.div 
      animate={{ 
        scale: isActive ? [1, 1.2, 1] : 1,
        opacity: isActive ? [0.5, 0.8, 0.5] : 0.3 
      }}
      transition={{ repeat: Infinity, duration: isActive ? 1.5 : 3 }}
      className="absolute inset-0 rounded-full bg-ai-pink/30 blur-2xl"
    />
    <motion.div 
      animate={{ 
        scale: isActive ? [1, 1.1, 1] : 1,
        rotate: isActive ? 180 : 0
      }}
      transition={{ repeat: Infinity, duration: 4, ease: "linear" }}
      className="absolute inset-2 rounded-full border border-ai-purple/50 bg-gradient-to-tr from-ai-purple/20 to-ai-pink/20"
    />
    {/* Core Orb */}
    <motion.div 
      animate={{ scale: isActive ? [1, 0.95, 1] : 1 }}
      transition={{ repeat: Infinity, duration: 1 }}
      className="relative z-10 w-3/4 h-3/4 rounded-full bg-gradient-to-br from-ai-pink via-ai-purple to-ai-cyan orb-glow flex items-center justify-center shadow-[0_0_50px_rgba(255,126,179,0.8)]"
    >
      <div className="absolute inset-0 rounded-full bg-white/20 blur-md" />
      <Mic className={`text-white w-1/3 h-1/3 z-20 ${isActive ? 'animate-pulse' : ''}`} />
    </motion.div>
  </div>
);

// ==========================================
// TABS
// ==========================================

function Dashboard() {
  const [devices, setDevices] = useState({});

  useEffect(() => {
    // Mock data for UI presentation since local API might be offline
    setDevices({
      'light_1': 'ON',
      'fan_1': 'OFF',
      'curtain_1': 'ON'
    });
    
    // In a real scenario, uncomment the polling below:
    /*
    const fetchStates = async () => {
      try {
        const res = await axios.get(`${API_BASE}/devices/state`);
        setDevices(res.data.devices);
      } catch (err) { }
    };
    fetchStates();
    const interval = setInterval(fetchStates, 3000);
    return () => clearInterval(interval);
    */
  }, []);

  const toggleDevice = (id, currentState) => {
    const action = currentState === 'ON' ? 'OFF' : 'ON';
    setDevices(prev => ({ ...prev, [id]: action }));
    // In real app, send post request here.
  };

  const activeCount = Object.values(devices).filter(v => v === 'ON').length;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-6 pb-24">
      
      {/* Hero Section */}
      <div className="text-center py-6">
        <AiOrb isActive={true} size="w-24 h-24" />
        <h2 className="mt-6 text-3xl font-black bg-clip-text text-transparent bg-gradient-to-r from-ai-pink to-ai-cyan">
          Hello, I'm Kasu.
        </h2>
        <p className="text-gray-400 mt-2 text-sm flex items-center justify-center gap-2">
          <Languages className="w-4 h-4 text-ai-purple" /> English & Sinhala Voice Assistant
        </p>
      </div>

      <div className="glass-panel p-6 rounded-3xl flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Settings2 className="text-ai-pink" /> Home Automation
          </h2>
          <p className="text-gray-400 text-sm mt-1">Live Device Status</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-black text-ai-cyan">{activeCount}</div>
          <div className="text-xs text-gray-400 uppercase tracking-widest font-bold mt-1">Active</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {['light_1', 'fan_1', 'curtain_1'].map((device) => {
          const isOn = devices[device] === 'ON';
          return (
            <motion.div 
              key={device}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => toggleDevice(device, devices[device] || 'OFF')}
              className={`cursor-pointer p-6 rounded-3xl glass-panel transition-all duration-300 flex items-center justify-between ${
                isOn ? 'border-ai-cyan/50 shadow-[0_0_30px_rgba(0,243,255,0.15)] bg-gradient-to-r from-ai-cyan/10 to-transparent' : ''
              }`}
            >
              <div>
                <h3 className="text-lg font-bold capitalize tracking-wide">{device.replace('_', ' ')}</h3>
                <p className={`text-xs font-bold tracking-widest mt-1 ${isOn ? 'text-ai-cyan' : 'text-gray-500'}`}>
                  {isOn ? 'ACTIVE' : 'STANDBY'}
                </p>
              </div>
              <div className={`w-14 h-7 rounded-full flex items-center p-1 transition-colors duration-500 shadow-inner ${isOn ? 'bg-ai-cyan' : 'bg-gray-800'}`}>
                <motion.div layout className={`w-5 h-5 bg-white rounded-full shadow-md ${isOn ? 'ml-7' : 'ml-0'}`} />
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

function RegisterVoice() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [name, setName] = useState('');
  const [status, setStatus] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = e => chunksRef.current.push(e.data);
      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const wavBlob = await convertToWav(blob);
        setAudioBlob(wavBlob);
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
      setStatus('Recording...');
      
      setTimeout(() => {
        if(mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          stopRecording();
        }
      }, 5000); // 5 sec for enrollment
      
    } catch (err) {
      console.error(err);
      setStatus('Microphone permission denied.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus('Voice captured perfectly. Ready to save.');
    }
  };

  const uploadVoice = async () => {
    if (!audioBlob || !name) return;
    setStatus('Extracting unique voice fingerprint...');
    
    const formData = new FormData();
    formData.append('audio', audioBlob, 'enroll.wav');
    formData.append('name', name);

    try {
      // Mocking successful response for demo
      setTimeout(() => {
        setStatus(`✅ Biometrics secured for ${name}!`);
        setAudioBlob(null);
        setName('');
      }, 1500);
    } catch (err) {
      setStatus(`❌ Failed to enroll`);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="glass-panel p-8 rounded-3xl max-w-lg mx-auto w-full pb-24">
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-full bg-ai-purple/20 flex items-center justify-center mx-auto mb-4 border border-ai-purple/30">
          <ShieldCheck className="w-8 h-8 text-ai-purple" />
        </div>
        <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">Biometric Registration</h2>
        <p className="text-gray-400 mt-2 text-sm">Add your voice to Kasu's secure whitelist.</p>
      </div>

      <div className="space-y-8">
        <div>
          <label className="block text-xs uppercase tracking-widest font-bold text-gray-400 mb-2 pl-1">Your Name</label>
          <input 
            type="text" 
            value={name} 
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-black/40 border border-gray-700 rounded-2xl px-5 py-4 text-white focus:outline-none focus:border-ai-pink focus:ring-1 focus:ring-ai-pink transition-all placeholder-gray-600"
            placeholder="e.g. Kasundi"
          />
        </div>

        <div className="flex flex-col items-center justify-center py-6">
           <div className="mb-6 cursor-pointer" onClick={isRecording ? stopRecording : startRecording}>
              <AiOrb isActive={isRecording} size="w-28 h-28" />
           </div>
          <p className="text-sm font-medium text-gray-300 h-6">{status || "Tap Kasu to record a 5s phrase"}</p>
        </div>

        <button 
          onClick={uploadVoice}
          disabled={!audioBlob || !name}
          className="w-full bg-gradient-to-r from-ai-pink to-ai-purple text-white font-bold py-4 rounded-2xl disabled:opacity-30 disabled:cursor-not-allowed hover:shadow-[0_0_20px_rgba(255,126,179,0.4)] transition-all flex items-center justify-center gap-2"
        >
          <Save className="w-5 h-5" /> Save Biometric Profile
        </button>
      </div>
    </motion.div>
  );
}

function TestVoice() {
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState('');
  const [result, setResult] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = e => chunksRef.current.push(e.data);
      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const wavBlob = await convertToWav(blob);
        await testAudio(wavBlob);
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
      setResult(null);
      setStatus('Listening to your command...');
      
      setTimeout(() => {
        if(mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
          setIsRecording(false);
          setStatus('Kasu is processing...');
        }
      }, 4000); 
      
    } catch (err) {
      console.error(err);
      setStatus('Microphone permission denied.');
    }
  };

  const testAudio = async (audioBlob) => {
    // Mock processing delay for demo
    setTimeout(() => {
        setResult({
            authorized: true,
            user_name: "Kasundi",
            command: "Turn ON the light_1",
            confidence: 96.3,
            sinhala: "ලයිට් එක දාන්න"
        });
        setStatus('');
    }, 1500);
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="glass-panel p-8 rounded-3xl max-w-2xl mx-auto w-full pb-24">
      <div className="text-center mb-8">
        <Zap className="w-12 h-12 text-ai-cyan mx-auto mb-4 drop-shadow-[0_0_15px_rgba(0,243,255,0.5)]" />
        <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-ai-cyan to-white">AI Control Center</h2>
        <p className="text-gray-400 mt-2 text-sm">Test Kasu's Sinhala recognition and biometric security.</p>
      </div>

      <div className="flex flex-col items-center justify-center py-8">
         <div className="cursor-pointer mb-6" onClick={isRecording ? () => {} : startRecording}>
             <AiOrb isActive={isRecording} size="w-32 h-32" />
         </div>
        <p className="font-mono text-sm text-ai-pink">{status || "Tap Kasu and speak!"}</p>
      </div>

      <AnimatePresence>
        {result && (
          <motion.div 
            initial={{ opacity: 0, height: 0, y: 20 }} 
            animate={{ opacity: 1, height: 'auto', y: 0 }} 
            className="bg-black/50 rounded-2xl p-6 border border-white/10 mt-6 overflow-hidden backdrop-blur-xl"
          >
            <h3 className="text-sm uppercase tracking-widest font-bold text-gray-400 mb-6 flex items-center gap-2">
               <Activity className="w-4 h-4 text-ai-cyan" /> Processing Results
            </h3>
            <div className="space-y-5">
              <div className="flex justify-between items-center bg-white/5 p-3 rounded-xl">
                <span className="text-gray-300 text-sm">Biometric Lock</span>
                {result.authorized ? (
                  <span className="text-ai-cyan font-bold text-sm bg-ai-cyan/10 px-3 py-1 rounded-full border border-ai-cyan/30">Verified ({result.user_name})</span>
                ) : (
                  <span className="text-red-400 font-bold text-sm bg-red-400/10 px-3 py-1 rounded-full">Rejected</span>
                )}
              </div>
              <div className="flex justify-between items-center bg-white/5 p-3 rounded-xl">
                <span className="text-gray-300 text-sm">Transcribed (Sinhala)</span>
                <span className="text-white font-bold">{result.sinhala}</span>
              </div>
              <div className="flex justify-between items-center bg-white/5 p-3 rounded-xl">
                <span className="text-gray-300 text-sm">Action Parsed</span>
                <span className="text-ai-pink font-bold">{result.command}</span>
              </div>
            </div>
            
            {result.authorized && result.command !== "UNKNOWN" && (
              <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }} className="mt-6 bg-gradient-to-r from-ai-cyan/20 to-ai-purple/20 text-white text-center py-4 rounded-xl border border-ai-cyan/30 font-bold tracking-wide shadow-[0_0_20px_rgba(0,243,255,0.1)]">
                Command Executed Successfully
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Header */}
      <header className="fixed top-0 w-full z-50 bg-dark-bg/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-center">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              KASU <span className="bg-clip-text text-transparent bg-gradient-to-r from-ai-pink to-ai-cyan">AI</span>
            </h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 pt-28 min-h-screen">
        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' && <Dashboard key="dashboard" />}
          {activeTab === 'register' && <RegisterVoice key="register" />}
          {activeTab === 'test' && <TestVoice key="test" />}
        </AnimatePresence>
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[90%] max-w-md glass-panel rounded-3xl px-6 py-4 z-50 shadow-[0_10px_40px_rgba(0,0,0,0.5)] border border-white/10">
        <div className="flex justify-between items-center">
          <NavItem icon={<Home />} label="Home" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
          <NavItem icon={<UserPlus />} label="Enroll" active={activeTab === 'register'} onClick={() => setActiveTab('register')} />
          <NavItem icon={<Play />} label="Interact" active={activeTab === 'test'} onClick={() => setActiveTab('test')} />
        </div>
      </nav>
    </div>
  );
}

function NavItem({ icon, label, active, onClick }) {
  return (
    <button onClick={onClick} className="relative flex flex-col items-center gap-1 group w-16">
      <div className={`p-3 rounded-2xl transition-all duration-300 ${active ? 'bg-gradient-to-tr from-ai-pink to-ai-purple text-white shadow-[0_0_15px_rgba(255,126,179,0.5)]' : 'text-gray-500 group-hover:text-white'}`}>
        {React.cloneElement(icon, { className: 'w-6 h-6' })}
      </div>
      <span className={`text-[10px] uppercase tracking-widest font-bold mt-1 transition-colors ${active ? 'text-white' : 'text-transparent'}`}>{label}</span>
    </button>
  );
}

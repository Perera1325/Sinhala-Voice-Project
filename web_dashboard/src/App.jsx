import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Activity, Home, Save, Play, X, UserPlus, Zap } from 'lucide-react';
import axios from 'axios';

// ==========================================
// CONFIGURATION
// ==========================================
// When deploying to Firebase, change this to your ngrok URL or RPi IP if not on the same network
const API_BASE = 'https://spicy-hairs-read.loca.lt/api';

// Bypass localtunnel warning screen
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
// COMPONENTS
// ==========================================

function Dashboard() {
  const [devices, setDevices] = useState({});

  useEffect(() => {
    const fetchStates = async () => {
      try {
        const res = await axios.get(`${API_BASE}/devices/state`);
        setDevices(res.data.devices);
      } catch (err) {
        console.error('Failed to fetch dashboard states', err);
      }
    };
    fetchStates();
    const interval = setInterval(fetchStates, 3000);
    return () => clearInterval(interval);
  }, []);

  const toggleDevice = async (id, currentState) => {
    const action = currentState === 'ON' ? 'OFF' : 'ON';
    try {
      await axios.post(`${API_BASE}/devices/control`, { device_id: id, action });
      // Optimistic update
      setDevices(prev => ({ ...prev, [id]: action }));
    } catch (err) {
      console.error('Failed to toggle device', err);
    }
  };

  const activeCount = Object.values(devices).filter(v => v === 'ON').length;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between p-6 bg-card-bg rounded-2xl border border-neon-blue/20 shadow-[0_0_15px_rgba(0,243,255,0.1)]">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity className="text-neon-blue" /> System Status
          </h2>
          <p className="text-gray-400 mt-1">Live from Raspberry Pi 4</p>
        </div>
        <div className="text-right">
          <div className="text-4xl font-black text-neon-blue">{activeCount}</div>
          <div className="text-sm text-gray-400 uppercase tracking-widest">Active Devices</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {['light_1', 'fan_1', 'curtain_1'].map((device) => {
          const isOn = devices[device] === 'ON';
          return (
            <motion.div 
              key={device}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => toggleDevice(device, devices[device] || 'OFF')}
              className={`cursor-pointer p-6 rounded-2xl border transition-all duration-300 flex items-center justify-between ${
                isOn ? 'bg-neon-blue/10 border-neon-blue shadow-[0_0_20px_rgba(0,243,255,0.2)]' : 'bg-card-bg border-gray-800 hover:border-gray-600'
              }`}
            >
              <div>
                <h3 className="text-xl font-bold capitalize">{device.replace('_', ' ')}</h3>
                <p className={`text-sm mt-1 ${isOn ? 'text-neon-blue' : 'text-gray-500'}`}>{isOn ? 'ACTIVE' : 'OFFLINE'}</p>
              </div>
              <div className={`w-12 h-6 rounded-full flex items-center p-1 transition-colors ${isOn ? 'bg-neon-blue' : 'bg-gray-800'}`}>
                <motion.div layout className={`w-4 h-4 bg-white rounded-full ${isOn ? 'ml-6' : 'ml-0'}`} />
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
      
      // Auto stop after 3 seconds
      setTimeout(() => {
        if(mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          stopRecording();
        }
      }, 3000);
      
    } catch (err) {
      console.error(err);
      setStatus('Microphone permission denied.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus('Recording finished. Ready to upload.');
    }
  };

  const uploadVoice = async () => {
    if (!audioBlob || !name) return;
    setStatus('Extracting Voice Fingerprint...');
    
    const formData = new FormData();
    formData.append('audio', audioBlob, 'enroll.wav');
    formData.append('name', name);

    try {
      const res = await axios.post(`${API_BASE}/users/enroll`, formData);
      setStatus(`✅ ${res.data.message}`);
      setAudioBlob(null);
      setName('');
    } catch (err) {
      setStatus(`❌ ${err.response?.data?.error || 'Failed to enroll'}`);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="bg-card-bg p-8 rounded-2xl border border-gray-800 max-w-lg mx-auto w-full">
      <div className="text-center mb-8">
        <UserPlus className="w-12 h-12 text-neon-purple mx-auto mb-4" />
        <h2 className="text-2xl font-bold">Biometric Registration</h2>
        <p className="text-gray-400 mt-2">Add a family member to the secure database.</p>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Member Name</label>
          <input 
            type="text" 
            value={name} 
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-neon-purple focus:ring-1 focus:ring-neon-purple transition-all"
            placeholder="e.g. Kasun"
          />
        </div>

        <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-gray-700 rounded-xl relative overflow-hidden">
          {isRecording && (
            <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 1.5 }} className="absolute inset-0 bg-neon-purple/10" />
          )}
          
          <button 
            onClick={isRecording ? stopRecording : startRecording}
            className={`z-10 relative w-20 h-20 rounded-full flex items-center justify-center transition-all ${isRecording ? 'bg-red-500 shadow-[0_0_30px_rgba(239,68,68,0.5)]' : 'bg-neon-purple shadow-[0_0_20px_rgba(188,19,254,0.3)] hover:scale-105'}`}
          >
            {isRecording ? <div className="w-6 h-6 bg-white rounded-sm" /> : <Mic className="w-8 h-8 text-white" />}
          </button>
          
          <p className="mt-4 text-sm font-medium text-gray-300 z-10">{status || "Tap to record 3s phrase"}</p>
        </div>

        <button 
          onClick={uploadVoice}
          disabled={!audioBlob || !name}
          className="w-full bg-neon-purple text-white font-bold py-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed hover:bg-neon-purple/80 transition-all flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(188,19,254,0.3)]"
        >
          <Save className="w-5 h-5" /> Save Biometrics
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
      setStatus('Listening...');
      
      setTimeout(() => {
        if(mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
          setIsRecording(false);
          setStatus('Processing AI Pipeline...');
        }
      }, 2000); // 2 second command
      
    } catch (err) {
      console.error(err);
      setStatus('Microphone permission denied.');
    }
  };

  const testAudio = async (audioBlob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'test.wav');

    try {
      const res = await axios.post(`${API_BASE}/voice/test`, formData);
      setResult(res.data);
      setStatus('');
    } catch (err) {
      setStatus(`❌ Error running AI`);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="bg-card-bg p-8 rounded-2xl border border-gray-800 max-w-2xl mx-auto w-full">
      <div className="text-center mb-8">
        <Zap className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold">AI Pipeline Arena</h2>
        <p className="text-gray-400 mt-2">Test your wake word, biometrics, and command simultaneously.</p>
      </div>

      <div className="flex flex-col items-center justify-center py-12">
        <button 
          onClick={startRecording}
          disabled={isRecording}
          className={`w-32 h-32 rounded-full flex items-center justify-center transition-all ${isRecording ? 'bg-red-500 scale-110 shadow-[0_0_50px_rgba(239,68,68,0.5)]' : 'bg-gradient-to-tr from-neon-blue to-neon-purple shadow-[0_0_30px_rgba(0,243,255,0.4)] hover:scale-105'}`}
        >
          {isRecording ? <Activity className="w-12 h-12 text-white animate-pulse" /> : <Mic className="w-12 h-12 text-white" />}
        </button>
        <p className="mt-6 font-mono text-gray-300">{status || "Say 'Hey Kasu' + Command"}</p>
      </div>

      <AnimatePresence>
        {result && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }} 
            animate={{ opacity: 1, height: 'auto' }} 
            className="bg-gray-900 rounded-xl p-6 border border-gray-700 mt-8 overflow-hidden"
          >
            <h3 className="text-lg font-bold text-gray-300 mb-4 border-b border-gray-800 pb-2">Analysis Results</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Security Gatekeeper:</span>
                {result.authorized ? (
                  <span className="text-green-400 font-bold bg-green-400/10 px-3 py-1 rounded-full">Passed ({result.user_name})</span>
                ) : (
                  <span className="text-red-400 font-bold bg-red-400/10 px-3 py-1 rounded-full">Rejected</span>
                )}
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Intent Detected:</span>
                <span className="text-neon-blue font-bold text-xl">{result.command}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">AI Confidence:</span>
                <span className="text-gray-200">{result.confidence}%</span>
              </div>
            </div>
            
            {result.authorized && result.command !== "UNKNOWN" && (
              <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} className="mt-6 bg-neon-blue/20 text-neon-blue text-center py-3 rounded-lg border border-neon-blue font-bold">
                Trigger Sent to Flask!
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
    <div className="min-h-screen pb-20">
      {/* Header */}
      <header className="border-b border-gray-800 bg-card-bg/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-gradient-to-tr from-neon-blue to-neon-purple flex items-center justify-center shadow-[0_0_10px_rgba(0,243,255,0.5)]">
              <Mic className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">KASU<span className="text-neon-blue">AI</span></h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' && <Dashboard key="dashboard" />}
          {activeTab === 'register' && <RegisterVoice key="register" />}
          {activeTab === 'test' && <TestVoice key="test" />}
        </AnimatePresence>
      </main>

      {/* Bottom Navigation (Mobile Friendly) */}
      <nav className="fixed bottom-0 w-full bg-card-bg border-t border-gray-800 px-6 py-4 z-50">
        <div className="max-w-md mx-auto flex justify-between">
          <NavItem icon={<Home />} label="Dashboard" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
          <NavItem icon={<UserPlus />} label="Register" active={activeTab === 'register'} onClick={() => setActiveTab('register')} />
          <NavItem icon={<Play />} label="Test AI" active={activeTab === 'test'} onClick={() => setActiveTab('test')} />
        </div>
      </nav>
    </div>
  );
}

function NavItem({ icon, label, active, onClick }) {
  return (
    <button onClick={onClick} className={`flex flex-col items-center gap-1 transition-colors ${active ? 'text-neon-blue' : 'text-gray-500 hover:text-gray-300'}`}>
      <div className={`p-2 rounded-xl transition-all ${active ? 'bg-neon-blue/10' : ''}`}>
        {React.cloneElement(icon, { className: 'w-6 h-6' })}
      </div>
      <span className="text-xs font-medium">{label}</span>
    </button>
  );
}

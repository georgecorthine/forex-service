import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_URL = 'http://localhost:8000';

function App() {
  const [status, setStatus] = useState({ service: 'offline', engine_running: false });
  const [logs, setLogs] = useState([]);
  const [pairs, setPairs] = useState([]);
  const [selectedPair, setSelectedPair] = useState('ALL');
  const logsEndRef = useRef(null);

  useEffect(() => {
    // Fetch available pairs configuration
    fetch(`${API_URL}/pairs`)
      .then(res => res.json())
      .then(data => setPairs(data))
      .catch(err => console.error("Failed to fetch pairs", err));

    const interval = setInterval(() => {
      // Fetch Status
      fetch(`${API_URL}/`)
        .then(res => res.json())
        .then(data => setStatus(data))
        .catch(err => console.error("Failed to fetch status", err));

      // Fetch Logs
      fetch(`${API_URL}/logs`)
        .then(res => res.json())
        .then(data => setLogs(data.logs))
        .catch(err => console.error("Failed to fetch logs", err));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to bottom of logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, selectedPair]);

  const toggleEngine = () => {
    const endpoint = status.engine_running ? '/control/stop' : '/control/start';
    fetch(`${API_URL}${endpoint}`, { method: 'POST' })
      .catch(err => console.error("Control error", err));
  };

  const filteredLogs = selectedPair === 'ALL' 
    ? logs 
    : logs.filter(log => log.includes(selectedPair));

  return (
    <div className="dashboard">
      <header>
        <h1>Forex Intelligence Dashboard</h1>
      </header>
      
      <div className="controls">
        <div className="status-box">
            <span>Service: {status.service}</span>
            <span>Engine: 
                <span className={status.engine_running ? "status-on" : "status-off"}>
                    {status.engine_running ? " RUNNING" : " STOPPED"}
                </span>
            </span>
        </div>
        <button className="control-btn" onClick={toggleEngine}>
            {status.engine_running ? "Stop Engine" : "Start Engine"}
        </button>
        <div className="filter-box">
            <label>Filter Pair: </label>
            <select value={selectedPair} onChange={(e) => setSelectedPair(e.target.value)}>
                <option value="ALL">ALL</option>
                {pairs.map(pair => <option key={pair} value={pair}>{pair}</option>)}
            </select>
        </div>
      </div>

      <div className="log-container">
        {filteredLogs.map((log, index) => (
            <div key={index} className="log-entry">{log}</div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}

export default App;
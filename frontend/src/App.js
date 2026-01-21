import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import TradeChart from './components/TradeChart';

const API_URL = 'http://localhost:8000';

function App() {
  const [status, setStatus] = useState({ service: 'offline', engine_running: false });
  const [logs, setLogs] = useState([]);
  const [pairs, setPairs] = useState([]);
  const [trades, setTrades] = useState([]);
  const [selectedPair, setSelectedPair] = useState('ALL');
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true); // New state to control auto-scrolling
  const logContainerRef = useRef(null); // Ref for the log container div
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
        .then(data => setLogs(data.logs || []))
        .catch(err => console.error("Failed to fetch logs", err));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Parse logs for trade data
  useEffect(() => {
    let analysisLogs = logs.filter(log => log.includes('Analysis ['));

    // If a specific pair is selected (and not 'ALL'), filter for that pair.
    if (selectedPair !== 'ALL') {
      analysisLogs = analysisLogs.filter(log => log.includes(selectedPair));
    } else if (analysisLogs.length > 0) {
      // If 'ALL' is selected, default to showing the first pair found in the logs to avoid mixing data.
      const firstPairMatch = analysisLogs[0].match(/\[(.*?)\]/);
      if (firstPairMatch && firstPairMatch[1]) {
        const firstPair = firstPairMatch[1];
        analysisLogs = analysisLogs.filter(log => log.includes(firstPair));
      }
    }
    
    const parsedTrades = analysisLogs.map((log, index) => {
      const priceMatch = log.match(/Price=([\d.]+)/);
      const timeMatch = log.match(/(\d{2}:\d{2}:\d{2})/); // Try to find a time string

      if (priceMatch && priceMatch[1]) {
        return {
          date: timeMatch ? timeMatch[1] : index, // Use time or index as x-axis
          price: parseFloat(priceMatch[1])
        };
      }
      return null;
    }).filter(Boolean);

    setTrades(parsedTrades);
  }, [logs, selectedPair]);

  // Auto-scroll to bottom of logs if shouldAutoScroll is true
  useEffect(() => {
    if (shouldAutoScroll) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, selectedPair, shouldAutoScroll]); // Add shouldAutoScroll to dependencies

  // Handle user scrolling to disable/enable auto-scroll
  const handleScroll = () => {
    const { scrollTop, scrollHeight, clientHeight } = logContainerRef.current;
    // If the user has scrolled to the very bottom, re-enable auto-scroll
    // Add a small buffer (e.g., 1px) to account for potential sub-pixel rendering differences
    if (scrollHeight - scrollTop <= clientHeight + 1) {
      setShouldAutoScroll(true);
    } else {
      setShouldAutoScroll(false);
    }
  };

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

      <div className="chart-container" style={{ marginBottom: '20px' }}>
        <TradeChart data={trades} />
      </div>

      <div className="log-container" ref={logContainerRef} onScroll={handleScroll}>
        {filteredLogs.map((log, index) => (
            <div key={index} className="log-entry">{log}</div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}

export default App;
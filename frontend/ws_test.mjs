const ws = new WebSocket("wss://nexstreamnewsengine.duckdns.org/api/ws/feed");
const timer = setTimeout(() => { console.log("TIMEOUT"); process.exit(1); }, 8000);
ws.onopen = () => { console.log("OPEN"); };
ws.onmessage = (e) => { console.log("MESSAGE:", e.data.slice(0,200)); clearTimeout(timer); ws.close(); process.exit(0); };
ws.onerror = (e) => { console.log("ERROR", e.message || e); };
ws.onclose = (e) => { console.log("CLOSE code=", e.code, "reason=", e.reason); clearTimeout(timer); process.exit(0); };

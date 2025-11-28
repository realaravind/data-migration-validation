import { useEffect, useState } from 'react';

export default function ValidationDashboard() {
    const [rows, setRows] = useState([]);

    useEffect(() => {
        fetch("http://localhost:8000/execution/results")
            .then(res => res.json())
            .then(data => setRows(data.results));
    }, []);

    return (
        <div style={{ padding: 20 }}>
            <h2>Validation Dashboard</h2>
            <pre>{JSON.stringify(rows, null, 2)}</pre>
        </div>
    );
}
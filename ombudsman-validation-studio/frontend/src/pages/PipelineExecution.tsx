import { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  Divider
} from "@mui/material";

export default function PipelineExecution() {
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [metadata, setMetadata] = useState<any>({});
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    const loadInitial = () => {
      const savedPipeline = JSON.parse(localStorage.getItem("columnMapping") || "{}");
      const schema = JSON.parse(localStorage.getItem("schema") || "{}");

      setPipeline(savedPipeline || []);
      setMetadata(schema || {});
    };

    loadInitial();
    loadLogs();
  }, []);

  const run = async () => {
    await fetch("/execution/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pipeline,
        metadata
      })
    });

    await loadLogs();
  };

  const loadLogs = async () => {
    const res = await fetch("/execution/logs", { method: "POST" });
    const data = await res.json();
    setLogs(data.logs || []);
  };

  return (
    <Box>
      <Typography variant="h4" mb={3}>
        Execution & Logs
      </Typography>

      <Button variant="contained" onClick={run}>
        Run Pipeline
      </Button>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6">Execution Logs</Typography>

          <List>
            {logs.map((log, idx) => (
              <Box key={idx}>
                <ListItem>
                  <ListItemText
                    primary={`${log.timestamp} — ${log.status}`}
                    secondary={JSON.stringify(log.output, null, 2)}
                  />
                </ListItem>
                <Divider />
              </Box>
            ))}
          </List>
        </CardContent>
      </Card>
    </Box>
  );
}
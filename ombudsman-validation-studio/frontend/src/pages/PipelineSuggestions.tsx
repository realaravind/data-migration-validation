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
  TextField
} from "@mui/material";

export default function PipelineSuggestions() {
  const [steps, setSteps] = useState<string[]>([]);
  const [metadata, setMetadata] = useState<any>({});

  useEffect(() => {
    const schema = JSON.parse(localStorage.getItem("schema") || "{}");
    setMetadata({ source: schema.source || [] });
    loadPipeline();
  }, []);

  const generate = async () => {
    const res = await fetch("/pipeline/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metadata })
    });
    const data = await res.json();
    setSteps(data.steps || []);
  };

  const savePipeline = async () => {
    await fetch("/pipeline/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ steps })
    });
    alert("Pipeline Saved");
  };

  const loadPipeline = async () => {
    try {
      const res = await fetch("/pipeline/load", { method: "POST" });
      const data = await res.json();
      setSteps(data.steps || []);
    } catch (_) {}
  };

  const updateStep = (idx: number, value: string) => {
    const updated = [...steps];
    updated[idx] = value;
    setSteps(updated);
  };

  const addStep = () => {
    setSteps([...steps, ""]);
  };

  return (
    <Box>
      <Typography variant="h4" mb={3}>Pipeline Suggestions (AI)</Typography>

      <Button variant="contained" onClick={generate} sx={{ mb: 2 }}>
        Generate Suggestions
      </Button>

      <Button onClick={addStep} sx={{ mx: 2 }}>
        Add Step
      </Button>

      <Button variant="contained" color="success" onClick={savePipeline}>
        Save
      </Button>

      <Button sx={{ ml: 2 }} onClick={loadPipeline}>
        Load
      </Button>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" mb={2}>Suggested Steps</Typography>

          <List>
            {steps.map((step, idx) => (
              <ListItem key={idx}>
                <TextField
                  fullWidth
                  value={step}
                  onChange={(e) => updateStep(idx, e.target.value)}
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
    </Box>
  );
}
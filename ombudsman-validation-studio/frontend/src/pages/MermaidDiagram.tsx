import { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  TextField
} from "@mui/material";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false });

interface MermaidDiagramProps {
    currentProject?: any;
}

export default function MermaidDiagram(_props: MermaidDiagramProps) {
  const [text, setText] = useState("graph TD;\n    A[Start] --> B[End]");
  const [svg, setSvg] = useState("");

  useEffect(() => {
    renderDiagram(text);
  }, []);

  const renderDiagram = async (src: string) => {
    try {
      const { svg } = await mermaid.render("diagram", src);
      setSvg(svg);
    } catch (e) {
      setSvg(`<div style='color:red'>Invalid Mermaid Syntax</div>`);
    }
  };

  const saveDiagram = async () => {
    await fetch("/mermaid/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diagram: text })
    });
    alert("Diagram Saved");
  };

  const loadDiagram = async () => {
    const res = await fetch("/mermaid/load", { method: "POST" });
    const data = await res.json();
    setText(data.diagram || "");
    renderDiagram(data.diagram || "");
  };

  const autoGenerate = async () => {
    const payload = { sample: "pipeline" }; // placeholder or real metadata later

    const res = await fetch("/mermaid/auto-generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    setText(data.diagram);
    renderDiagram(data.diagram);
  };

  return (
    <Box>
      <Typography variant="h4" mb={3}>
        Mermaid Diagram Editor
      </Typography>

      <Grid container spacing={3}>

        {/* LEFT SIDE: EDITOR */}
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={2}>Editor</Typography>

              <TextField
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  renderDiagram(e.target.value);
                }}
                multiline
                rows={20}
                fullWidth
              />

              <Box mt={2} display="flex" gap={1}>
                <Button variant="contained" onClick={saveDiagram}>
                  Save
                </Button>
                <Button variant="outlined" onClick={loadDiagram}>
                  Load
                </Button>
                <Button variant="contained" color="secondary" onClick={autoGenerate}>
                  Auto‑Generate
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* RIGHT SIDE: PREVIEW */}
        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={2}>Preview</Typography>

              <div
                dangerouslySetInnerHTML={{ __html: svg }}
                style={{ overflowX: "auto" }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
import { useState } from 'react';
import { Box, Button, TextareaAutosize } from '@mui/material';

interface PipelineYamlEditorProps {
    currentProject?: any;
}

export default function PipelineYamlEditor(_props: PipelineYamlEditorProps) {
    const [yaml, setYaml] = useState("");

    const runPipeline = async () => {
        const response = await fetch(__API_URL__ + "/execution/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ yaml_content: yaml })
        });
        const result = await response.json();
        alert(JSON.stringify(result, null, 2));
    };

    return (
        <Box p={4}>
            <h2>YAML Pipeline Editor</h2>
            <TextareaAutosize
                minRows={25}
                style={{ width: "100%", fontFamily: "monospace", fontSize: 14 }}
                value={yaml}
                onChange={(e) => setYaml(e.target.value)}
            />
            <Button variant="contained" sx={{ mt: 2 }} onClick={runPipeline}>
                Run Pipeline
            </Button>
        </Box>
    );
}
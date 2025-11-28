import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  List,
  ListItem,
  ListItemText
} from "@mui/material";

export default function MetadataExtraction() {
  const [connection, setConnection] = useState("");
  const [table, setTable] = useState("");
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const extractMetadata = async () => {
    setLoading(true);

    const res = await fetch("/metadata/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        connection,
        table
      })
    });

    const data = await res.json();
    setLoading(false);

    setColumns(data.columns || []);

    // Save to local storage so Mapping + Rules + Pipeline modules can use it
    localStorage.setItem(
      "schema",
      JSON.stringify({ source: data.columns || [] })
    );
  };

  return (
    <Box>
      <Typography variant="h4" mb={3}>
        Metadata Extraction
      </Typography>

      <Card>
        <CardContent>
          <Typography variant="h6" mb={2}>
            Database Info
          </Typography>

          <TextField
            fullWidth
            label="Connection String"
            value={connection}
            onChange={(e) => setConnection(e.target.value)}
            sx={{ mb: 2 }}
          />

          <TextField
            fullWidth
            label="Table Name"
            value={table}
            onChange={(e) => setTable(e.target.value)}
            sx={{ mb: 2 }}
          />

          <Button
            variant="contained"
            onClick={extractMetadata}
            disabled={loading}
          >
            {loading ? "Extracting..." : "Extract Metadata"}
          </Button>
        </CardContent>
      </Card>

      {columns.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" mb={2}>
              Extracted Columns
            </Typography>

            <List>
              {columns.map((c, idx) => (
                <ListItem key={idx}>
                  <ListItemText primary={c} />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
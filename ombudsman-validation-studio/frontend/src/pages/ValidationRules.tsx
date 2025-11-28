import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  TextField,
  MenuItem
} from "@mui/material";

export default function ValidationRules() {
  const [rules, setRules] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);

  useEffect(() => {
    const schema = JSON.parse(localStorage.getItem("schema") || "{}");
    setColumns(schema.source || []);
    loadRules();
  }, []);

  const addRule = () => {
    setRules([
      ...rules,
      {
        column: "",
        operator: "",
        value: "",
        severity: "error",
        description: ""
      }
    ]);
  };

  const updateRule = (idx: number, key: string, val: string) => {
    const updated = [...rules];
    updated[idx][key] = val;
    setRules(updated);
  };

  const saveRules = async () => {
    await fetch("/rules/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rules })
    });
    alert("Rules Saved");
  };

  const loadRules = async () => {
    try {
      const res = await fetch("/rules/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      const data = await res.json();
      setRules(data.rules || []);
    } catch (_) {}
  };

  return (
    <Box>
      <Typography variant="h4" mb={3}>Validation Rules</Typography>

      <Button variant="contained" onClick={addRule} sx={{ mb: 2 }}>
        Add Rule
      </Button>

      <Grid container spacing={3}>
        {rules.map((rule, idx) => (
          <Grid item xs={12} md={6} key={idx}>
            <Card>
              <CardContent>
                <Typography variant="h6" mb={2}>
                  Rule {idx + 1}
                </Typography>

                <TextField
                  label="Column"
                  fullWidth
                  select
                  value={rule.column}
                  onChange={(e) =>
                    updateRule(idx, "column", e.target.value)
                  }
                  sx={{ mb: 2 }}
                >
                  {columns.map((c) => (
                    <MenuItem key={c} value={c}>
                      {c}
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  label="Operator"
                  fullWidth
                  select
                  value={rule.operator}
                  onChange={(e) =>
                    updateRule(idx, "operator", e.target.value)
                  }
                  sx={{ mb: 2 }}
                >
                  <MenuItem value="=">=</MenuItem>
                  <MenuItem value="!=">!=</MenuItem>
                  <MenuItem value=">">{'>'}</MenuItem>
                  <MenuItem value="<">{'<'}</MenuItem>
                  <MenuItem value="contains">contains</MenuItem>
                  <MenuItem value="not_contains">not contains</MenuItem>
                  <MenuItem value="regex">regex</MenuItem>
                  <MenuItem value="not_null">not null</MenuItem>
                  <MenuItem value="null">null</MenuItem>
                </TextField>

                <TextField
                  label="Value"
                  fullWidth
                  value={rule.value}
                  onChange={(e) =>
                    updateRule(idx, "value", e.target.value)
                  }
                  sx={{ mb: 2 }}
                />

                <TextField
                  label="Severity"
                  fullWidth
                  select
                  value={rule.severity}
                  onChange={(e) =>
                    updateRule(idx, "severity", e.target.value)
                  }
                  sx={{ mb: 2 }}
                >
                  <MenuItem value="error">error</MenuItem>
                  <MenuItem value="warning">warning</MenuItem>
                  <MenuItem value="info">info</MenuItem>
                </TextField>

                <TextField
                  label="Description"
                  fullWidth
                  multiline
                  rows={2}
                  value={rule.description}
                  onChange={(e) =>
                    updateRule(idx, "description", e.target.value)
                  }
                />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Button
        variant="contained"
        color="success"
        sx={{ mt: 3 }}
        onClick={saveRules}
      >
        Save Rules
      </Button>

      <Button sx={{ mt: 3, ml: 2 }} onClick={loadRules}>
        Load Rules
      </Button>
    </Box>
  );
}
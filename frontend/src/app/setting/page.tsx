"use client";
import React from "react";
import {
  Box,
  Container,
  Paper,
  ThemeProvider,
} from "@mui/material";
import { agineTheme, purpleTheme } from "@/theme/theme";
import ModelSetting from "@/componets/tabs/ModelSetting";


const SettingsPage = () => {
  return (
    <ThemeProvider theme={agineTheme}>
      <Box
        sx={{
          minHeight: "100vh",
          backgroundColor: purpleTheme.background.main,
          py: 4,
        }}
      >
        <Container maxWidth="md">
          <Paper
            elevation={3}
            sx={{
              p: 4,
              backgroundColor: purpleTheme.background.paper,
              border: `1px solid ${purpleTheme.secondary}40`,
            }}
          >
            <ModelSetting />
          </Paper>
        </Container>
      </Box>
    </ThemeProvider>
  );
};

export default SettingsPage;

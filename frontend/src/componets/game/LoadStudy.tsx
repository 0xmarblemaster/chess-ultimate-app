import { useState } from "react";
import { Box, Typography, TextField, Button } from "@mui/material";
import { purpleTheme } from "@/theme/theme";
import { Analytics } from "@mui/icons-material";
import { parsePgnChapters } from "@/libs/game/helper";

export interface Chapter {
    title: string;
    url: string;
    pgn: string;
}

interface GameLoaderProp {
    setChapters: (chapter: Chapter[]) => void;
    setInputsVisible: (view: boolean) => void;
}

function LoadStudy({setChapters, setInputsVisible}: GameLoaderProp) {

  const [studyUrl, setStudyUrl] = useState("");

  return (
    <Box>
      <Typography
        variant="h6"
        sx={{
          color: purpleTheme.text.accent,
          mb: 2,
          display: "flex",
          alignItems: "center",
        }}
      >
        <Analytics sx={{ mr: 1 }} />
        Lichess Study
      </Typography>
      <TextField
        fullWidth
        label="Paste Lichess Study URL"
        value={studyUrl}
        onChange={(e) => setStudyUrl(e.target.value)}
        placeholder="https://lichess.org/study/GuglnqGD"
        sx={{
          backgroundColor: purpleTheme.background.input,
          borderRadius: 2,
          mb: 2,
          "& .MuiOutlinedInput-root": {
            "& fieldset": {
              borderColor: purpleTheme.secondary,
            },
            "&:hover fieldset": {
              borderColor: purpleTheme.accent,
            },
            "&.Mui-focused fieldset": {
              borderColor: purpleTheme.accent,
            },
          },
        }}
        slotProps={{
          inputLabel: { sx: { color: purpleTheme.text.secondary } },
          input: { sx: { color: purpleTheme.text.primary } },
        }}
      />
      <Button
        variant="contained"
        fullWidth
        sx={{
          backgroundColor: purpleTheme.primary,
          "&:hover": { backgroundColor: purpleTheme.primaryDark },
          borderRadius: 2,
          py: 1.5,
          textTransform: "none",
          fontSize: "1rem",
        }}
        onClick={async () => {
          const idMatch = studyUrl.match(/study\/([a-zA-Z0-9]+)/);
          if (!idMatch) return alert("Invalid study URL");

          const res = await fetch(
            `https://lichess.org/api/study/${idMatch[1]}.pgn`
          );
          const text = await res.text();
          const parsed = parsePgnChapters(text);
          if (parsed.length === 0) return alert("No chapters found");

          setChapters(parsed);

          setInputsVisible(false);
        }}
      >
        Load Study
      </Button>
    </Box>
  );
}

export default LoadStudy;

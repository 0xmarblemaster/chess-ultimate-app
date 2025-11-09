"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  useMediaQuery,
  useTheme,
  Divider,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import {
  FaChessPawn,
  FaChessBoard,
  FaDiscord,
  FaPuzzlePiece,
  FaGear,
  FaBook
} from "react-icons/fa6";
import { GitHub } from "@mui/icons-material";

// Clerk authentication disabled for local development
// import { useClerk } from "@clerk/nextjs";
// import { SignedIn, SignedOut, UserButton } from "@clerk/nextjs";

export default function NavBar() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mounted, setMounted] = useState(false);
  const theme = useTheme();
  const mediaQuery = useMediaQuery(theme.breakpoints.down("md"));
  const router = useRouter();

  // Prevent hydration mismatch by only checking isMobile on client
  useEffect(() => {
    setMounted(true);
    setIsMobile(mediaQuery);
  }, [mediaQuery]);

  const handleLogoClick = () => {
    router.push("/");
  };

  const toggleDrawer = (open: boolean) => () => {
    setDrawerOpen(open);
  };

  // Return null during SSR to prevent hydration errors with Material-UI styling
  if (!mounted) {
    return (
      <div style={{ height: '64px', backgroundColor: '#111', marginBottom: '24px' }} suppressHydrationWarning />
    );
  }

  // Public navigation links (available to everyone)
  const publicNavLinks = [
    {
      label: "Docs",
      href: "/docs",
      icon: <FaBook />
    },
    {
      label: "Github",
      href: "https://github.com/jalpp/chessempireweb",
      icon: <GitHub/>
    },
    {
      label: "Discord",
      href: "https://discord.gg/3RpEnvmZwp",
      icon: <FaDiscord />,
    },
  ];

  const authNavLinks = [
    {
      label: "Analyze Position",
      href: "/position",
      icon: <FaChessBoard />
    },
    {
      label: "Analyze Game",
      href: "/game",
      icon: <FaChessPawn />
    },
    {
      label: "Puzzles",
      href: "/puzzle",
      icon: <FaPuzzlePiece />
    },
    {
      label: "Settings",
      href: "/setting",
      icon: <FaGear />
    },
  ];

  return (
    <>
      <AppBar position="static" sx={{ backgroundColor: "#111", mb: 3 }} suppressHydrationWarning>
        <Toolbar>
          <Typography
            variant="h6"
            sx={{
              flexGrow: 1,
              fontWeight: "bold",
              cursor: "pointer"
            }}
            onClick={handleLogoClick}
          >
            Chess Empire
          </Typography>

          {isMobile ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <IconButton color="inherit" onClick={toggleDrawer(true)}>
                <MenuIcon />
              </IconButton>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {/* Public links - always visible */}
              {publicNavLinks.map((link) => (
                <Button
                  key={link.href}
                  color="inherit"
                  href={link.href}
                  startIcon={link.icon}
                >
                  {link.label}
                </Button>
              ))}

              {/* Authenticated links - visible in no-auth mode for testing */}
              {authNavLinks.map((link) => (
                <Button
                  key={link.href}
                  color="inherit"
                  href={link.href}
                  startIcon={link.icon}
                >
                  {link.label}
                </Button>
              ))}
            </Box>
          )}
        </Toolbar>
      </AppBar>

      {/* Mobile Drawer */}
      <Drawer anchor="right" open={drawerOpen} onClose={toggleDrawer(false)}>
        <Box
          sx={{
            width: 280,
            bgcolor: "#111",
            height: "100%",
            color: "white",
          }}
          role="presentation"
          onClick={toggleDrawer(false)}
        >
          <List>
            {/* Public navigation items */}
            {publicNavLinks.map((link) => (
              <ListItem
                key={link.href}
                component="a"
                href={link.href}
                sx={{
                  textDecoration: "none",
                  color: "inherit",
                  "&:hover": {
                    bgcolor: "rgba(255, 255, 255, 0.1)",
                  },
                }}
              >
                <ListItemIcon sx={{ color: 'white', minWidth: 40 }}>
                  {link.icon}
                </ListItemIcon>
                <ListItemText primary={link.label} />
              </ListItem>
            ))}

            <Divider sx={{ my: 1, bgcolor: 'rgba(255, 255, 255, 0.3)' }} />

            {/* Authenticated navigation items */}
            {authNavLinks.map((link) => (
              <ListItem
                key={link.href}
                component="a"
                href={link.href}
                sx={{
                  textDecoration: "none",
                  color: "inherit",
                  "&:hover": {
                    bgcolor: "rgba(255, 255, 255, 0.1)",
                  },
                }}
              >
                <ListItemIcon sx={{ color: 'white', minWidth: 40 }}>
                  {link.icon}
                </ListItemIcon>
                <ListItemText primary={link.label} />
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
    </>
  );
}

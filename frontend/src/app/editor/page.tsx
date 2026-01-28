"use client";

import React, { Suspense } from "react";
import dynamic from "next/dynamic";

const BoardEditor = dynamic(() => import("@/components/editor/BoardEditor"), {
  ssr: false,
});

function EditorContent() {
  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#121212",
        color: "#ddd",
        paddingTop: "16px",
        paddingBottom: "80px",
      }}
    >
      <h1
        style={{
          textAlign: "center",
          fontSize: "20px",
          fontWeight: 600,
          marginBottom: "16px",
          color: "#ccc",
        }}
      >
        Board Editor
      </h1>
      <BoardEditor />
    </div>
  );
}

export default function EditorPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh",
            backgroundColor: "#121212",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#999",
          }}
        >
          Loading editor...
        </div>
      }
    >
      <EditorContent />
    </Suspense>
  );
}

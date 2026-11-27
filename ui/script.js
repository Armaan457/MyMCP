// Tailwind CSS Configuration
tailwind.config = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        midnight: '#050711',
        darkBlue: '#090d21',
        surface: '#0e1430',
        border: 'var(--accent-border)',
        accent: {
          primary: 'var(--accent-primary)',
          secondary: 'var(--accent-secondary)',
          light: 'var(--accent-light)',
          lighter: 'var(--accent-lighter)',
          border: 'var(--accent-border)',
          'border-hover': 'var(--accent-border-hover)',
          'badge-start': 'var(--accent-badge-start)',
          'badge-end': 'var(--accent-badge-end)',
          glow: 'var(--accent-glow)',
          'glow-subtle': 'var(--accent-glow-subtle)',
          ambient: 'var(--accent-ambient)',
          'muted-bg': 'var(--accent-muted-bg)',
        }
      }
    }
  }
};

// Copy endpoint function with visual feedback
function copyEndpoint() {
  const url = "https://mcp.armaanjagirdar.me/sse";
  navigator.clipboard.writeText(url).then(() => {
    const text = document.getElementById("copyText");
    const orig = text.innerText;
    text.innerText = "Copied!";
    setTimeout(() => {
      text.innerText = orig;
    }, 1800);
  });
}

// Copy Claude configuration JSON
function copyClaudeJSON() {
  const json = JSON.stringify({
    "mcpServers": {
      "armaan-profile": {
        "url": "https://mcp.armaanjagirdar.me/sse"
      }
    }
  }, null, 2);
  navigator.clipboard.writeText(json).then(() => {
    alert("Copied Claude Desktop configuration JSON to clipboard!");
  });
}

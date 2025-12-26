# How to Run generate_diagrams.py

## Current Status
✅ Python `diagrams` package is installed  
❌ Graphviz system dependency is **NOT** installed

## Error Message
```
graphviz.backend.execute.ExecutableNotFound: failed to execute PosixPath('dot'), 
make sure the Graphviz executables are on your system's PATH
```

## Solution: Install Graphviz

### Option 1: Using winget (Recommended - Easiest)
```powershell
winget install graphviz
```

After installation, **restart your terminal** or add to PATH manually.

### Option 2: Manual Download
1. Download from: https://graphviz.org/download/
2. Download the Windows installer (`.msi` file)
3. Run the installer
4. **IMPORTANT**: During installation, check "Add Graphviz to system PATH"
5. Restart your terminal

### Option 3: Using Chocolatey (if you have it)
```powershell
choco install graphviz
```

## After Installing Graphviz

1. **Restart your terminal** (or VS Code)
2. Verify installation:
   ```powershell
   dot -V
   ```
   Should output: `dot - graphviz version X.X.X`

3. Run the diagram generator:
   ```powershell
   python generate_diagrams.py
   ```

4. Check for generated PNG files:
   - `architecture_diagram.png`
   - `upload_flow_diagram.png`
   - `search_flow_diagram.png`

## Alternative: Use Mermaid Diagrams Instead

If you don't want to install Graphviz, you can use the **Mermaid diagrams** in `TECHNICAL_ARCHITECTURE.md`:

### View in VS Code:
1. Install extension: "Markdown Preview Mermaid Support"
2. Open `TECHNICAL_ARCHITECTURE.md`
3. Press `Ctrl+Shift+V` to preview

### View in GitHub:
- Just push the file - diagrams render automatically

### View Online:
1. Open https://mermaid.live/
2. Copy any diagram code from `TECHNICAL_ARCHITECTURE.md`
3. Paste and view

## Summary

**For PNG diagrams**: Install Graphviz (Option 1 recommended)  
**For quick viewing**: Use Mermaid diagrams in `TECHNICAL_ARCHITECTURE.md` (no installation needed)

Both approaches show the same architecture - choose based on your preference!

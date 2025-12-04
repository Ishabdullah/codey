# Codey Usage Guide

## Important: How to Use Codey Effectively

Codey uses a local CodeLlama-7B model, which works best with **simple, direct commands**.

### ✅ DO: Use Simple Commands

Give ONE command at a time:

```bash
codey> mkdir ~/ViralNexus_Project
codey> clone https://github.com/Ishabdullah/ViralNexus ~/ViralNexus_Project
codey> install requirements.txt
```

### ❌ DON'T: Give Complex Multi-Step Instructions

Avoid long, complex instructions like:
```bash
codey> You are Codey, my AI coding assistant. I want you to fully set up my ViralNexus project...
      [long paragraph with 7 steps]
```

**Why?** The local model (7B parameters) can get confused by complex instructions and may:
- Generate nonsensical responses
- Hallucinate incorrect steps
- "Talk to itself" instead of executing commands

---

## Command Structure

### File Operations (in workspace)
```bash
codey> create hello.py that prints hello world
codey> edit hello.py to add error handling
codey> read config.json
codey> delete old_test.py
```

### Git Operations (works anywhere!)
```bash
# Clone to any directory (use ~/ for home)
codey> clone https://github.com/user/repo ~/MyProject

# Git operations in current directory
codey> git status
codey> commit with message "Add new feature"
codey> push origin main
```

### Shell Operations (works anywhere!)
```bash
# Create directories anywhere
codey> mkdir ~/ViralNexus_Project

# Install packages
codey> install numpy
codey> install requirements.txt

# Run Python files
codey> run test.py

# Execute any shell command
codey> execute ls -la ~/ViralNexus_Project
```

---

## Setting Up a New Project (Step-by-Step)

### Example: Setting up ViralNexus

**Step 1: Create directory**
```bash
codey> mkdir ~/ViralNexus_Project
```
Wait for permission prompt, approve with `y`

**Step 2: Clone repository**
```bash
codey> clone https://github.com/Ishabdullah/ViralNexus ~/ViralNexus_Project
```
Wait for permission prompt, approve with `y`

**Step 3: Check for requirements**
```bash
codey> execute ls ~/ViralNexus_Project
```
Look for `requirements.txt`

**Step 4: Install dependencies**
```bash
codey> execute cd ~/ViralNexus_Project && pip install -r requirements.txt
```
Or if you need permission:
```bash
codey> install requirements.txt
```

**Step 5: Verify setup**
```bash
codey> execute ls -la ~/ViralNexus_Project
```

---

## Path Support

Codey now supports paths outside the workspace:

- **Absolute paths**: `/data/data/com.termux/files/home/myproject`
- **Home directory**: `~/myproject` or `$HOME/myproject`
- **Relative to workspace**: `myproject` (goes to ~/codey/workspace/myproject)

---

## Complex Tasks: Use Planning

For multi-step tasks, use the planning feature:

```bash
codey> plan Set up ViralNexus project with dependencies
```

Codey will break it down into steps, then:
```bash
codey> execute plan
```

This works better than giving complex instructions directly.

---

## Common Issues

### Issue: "Codey is talking to itself"
**Cause:** Complex instruction confused the local model
**Solution:** Use simple, one-step commands

### Issue: "Directory not created outside workspace"
**Cause:** Old version didn't support paths outside workspace
**Solution:** Update to latest version (now fixed!)

### Issue: "Permission required" appears mid-response
**Cause:** This is normal! Codey asks permission before operations
**Solution:** Respond with `y` or `n` when prompted

---

## Best Practices

1. **One command at a time** - Don't chain multiple operations
2. **Wait for completion** - Let each command finish before the next
3. **Use absolute paths** - Use `~/` for clarity
4. **Keep it simple** - The simpler the command, the better it works
5. **Use `execute` for shell commands** - Direct shell access when needed

---

## Quick Reference

| Task | Command |
|------|---------|
| Create dir anywhere | `mkdir ~/path/to/dir` |
| Clone repo anywhere | `clone <url> ~/destination` |
| Install packages | `install <package>` or `install requirements.txt` |
| Run shell command | `execute <command>` |
| Create file | `create <file> <description>` |
| Git status | `git status` |
| System info | `info` |
| Help | `help` |

---

## When to Use Claude Code Instead

For these tasks, use **Claude Code** (me, not Codey):
- Planning complex multi-step projects
- Refactoring large codebases
- Architectural decisions
- Understanding complex code
- Debugging intricate issues

Use **Codey** for:
- Quick file creation/editing
- Git operations
- Package installation
- Running commands
- Simple coding tasks

---

**Remember: Codey is a local 7B model. Keep commands simple and direct for best results!**

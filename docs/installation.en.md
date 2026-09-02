# Installation guide

[简体中文](installation.md)

This document explains how to install and verify files. It is not a second behavior, safety, or compatibility contract. See [`REQUIREMENTS.md`](../REQUIREMENTS.md) and [`SECURITY.md`](../SECURITY.md) for behavior and safety; see [Compatibility and evidence](compatibility-and-evidence.en.md) and the linked machine sources for runtime status.

The current stable source contract on `main` and the latest real public release are both v0.4.0. The pinned tag, archive, and checksum below jointly identify this immutable release; runtime compatibility remains a separate evidence-backed claim.

## Recommended

Open the Agent you already use—Claude Code, Codex, Cursor, OpenClaw, Hermes Agent, CodeBuddy, WorkBuddy, Gemini CLI, OpenCode, or another—and tell it:

```text
Install this Skill for me: https://github.com/zemu2718/think-it-through-skill
```

The Agent will try to install it using the current host's capabilities, permissions, and Skill-directory convention. Network or file access still requires authorization through that host. Automatic installation depends on the current host; listing these Agents does not mean they have all passed real-runtime validation.

## Alternatives

### Pinned universal installer

The published `.skill` is a ZIP-compatible archive containing only the manifest-declared runtime files. The pinned `skills` CLI can discover installation targets interactively:

```bash
npx -y skills@1.5.23 add \
  https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/think-it-through.skill
```

To install a copied, user-level package for every target known to that installer version:

```bash
npx -y skills@1.5.23 add \
  https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/think-it-through.skill \
  --agent '*' \
  --global \
  --copy \
  --yes
```

`--agent '*'` means all target mappings recognized by `skills@1.5.23`; it does **not** mean every AI client exists in that list or has passed real-runtime validation. Omit the flag for interactive target selection, or replace `'*'` with the exact target you want.

### GitHub CLI for Claude Code

With [GitHub CLI 2.98.0 or later](https://cli.github.com/), install it for Claude Code at user scope:

```bash
gh skill install \
  zemu2718/think-it-through-skill \
  think-it-through@v0.4.0 \
  --agent claude-code \
  --scope user
```

If the top-level Skill directory did not exist when your current Claude Code session started, restart Claude Code after installation.

### Manual fallback

If neither installer supports your host, copy the Skill directory according to that host's Agent Skills convention. For Claude Code:

```bash
git clone --depth 1 --branch v0.4.0 https://github.com/zemu2718/think-it-through-skill.git
cd think-it-through-skill
git rev-parse HEAD
test ! -e ~/.claude/skills/think-it-through
mkdir -p ~/.claude/skills
cp -R skills/think-it-through ~/.claude/skills/
```

The non-overwrite check stops if another copy already exists. Inspect that copy instead of merging versions; rename or remove it yourself before reinstalling.

## After installation

The reliable entry is explicit invocation in Claude Code:

```text
/think-it-through
```

Before installation, verify the archive with the published [`SHA256SUMS`](https://github.com/zemu2718/think-it-through-skill/releases/download/v0.4.0/SHA256SUMS). For a manual installation, use `git rev-parse HEAD` to record the exact source revision.

## What installation establishes

Whichever option you use, installation only places files in a target directory; it does not certify loading, behavior, or native capabilities in a particular runtime/version. See [Compatibility and evidence](compatibility-and-evidence.en.md) for the levels, current state, and evidence sources.

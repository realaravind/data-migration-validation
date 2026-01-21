# BMAD-METHOD™: Universal AI Agent Framework (v4 - Stable)

[![Version](https://img.shields.io/npm/v/bmad-method?color=blue&label=version)](https://www.npmjs.com/package/bmad-method)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D20.0.0-brightgreen)](https://nodejs.org)
[![Discord](https://img.shields.io/badge/Discord-Join%20Community-7289da?logo=discord&logoColor=white)](https://discord.gg/gk8jAdXWmj)

> ## 🚨 **v4 STABLE - NO NEW FEATURES** 🚨
>
> This is the **stable, production-ready v4 version** of BMad Method. It will receive **critical patches only** - no new features will be added.
>
> **Install v4 Stable:** `npx bmad-method install`

---

## 🆕 Want to Try v6 Alpha?

**BMad v6** is under active development with major improvements:

- Scale-adaptive workflows (Levels 0-4)
- Project-adaptive architecture
- Enhanced module system (BMM, BMB, CIS)
- Update-safe customization

**[View v6 Documentation](https://github.com/bmad-code-org/BMAD-METHOD/tree/main)** | **Install:** `npx bmad-method@alpha install`

> **Note:** v6 is in alpha - stable enough for testing but not production-ready yet.

---

Foundations in Agentic Agile Driven Development, known as the Breakthrough Method of Agile AI-Driven Development, yet so much more. Transform any domain with specialized AI expertise: software development, entertainment, creative writing, business strategy to personal wellness just to name a few.

**[Subscribe to BMadCode on YouTube](https://www.youtube.com/@BMadCode?sub_confirmation=1)**

**[Join our Discord Community](https://discord.gg/gk8jAdXWmj)** - A growing community for AI enthusiasts! Get help, share ideas, explore AI agents & frameworks, collaborate on tech projects, enjoy hobbies, and help each other succeed. Whether you're stuck on BMad, building your own agents, or just want to chat about the latest in AI - we're here for you! **Some mobile and VPN may have issue joining the discord, this is a discord issue - if the invite does not work, try from your own internet or another network, or non-VPN.**

⭐ **If you find this project helpful or useful, please give it a star in the upper right hand corner!** It helps others discover BMAD-METHOD™ and you will be notified of updates!

## Overview

**BMAD-METHOD™'s Two Key Innovations:**

**1. Agentic Planning:** Dedicated agents (Analyst, PM, Architect) collaborate with you to create detailed, consistent PRDs and Architecture documents. Through advanced prompt engineering and human-in-the-loop refinement, these planning agents produce comprehensive specifications that go far beyond generic AI task generation.

**2. Context-Engineered Development:** The Scrum Master agent then transforms these detailed plans into hyper-detailed development stories that contain everything the Dev agent needs - full context, implementation details, and architectural guidance embedded directly in story files.

This two-phase approach eliminates both **planning inconsistency** and **context loss** - the biggest problems in AI-assisted development. Your Dev agent opens a story file with complete understanding of what to build, how to build it, and why.

**📖 [See the complete workflow in the User Guide](docs/user-guide.md)** - Planning phase, development cycle, and all agent roles

## Quick Navigation

### Understanding the BMad Workflow

**Before diving in, review these critical workflow diagrams that explain how BMad works:**

1. **[Planning Workflow (Web UI)](docs/user-guide.md#the-planning-workflow-web-ui)** - How to create PRD and Architecture documents
2. **[Core Development Cycle (IDE)](docs/user-guide.md#the-core-development-cycle-ide)** - How SM, Dev, and QA agents collaborate through story files

> ⚠️ **These diagrams explain 90% of BMad Method Agentic Agile flow confusion** - Understanding the PRD+Architecture creation and the SM/Dev/QA workflow and how agents pass notes through story files is essential - and also explains why this is NOT taskmaster or just a simple task runner!

### What would you like to do?

- **[Install and Build software with Full Stack Agile AI Team](#quick-start)** → Quick Start Instruction
- **[Learn how to use BMad](docs/user-guide.md)** → Complete user guide and walkthrough
- **[See available AI agents](/bmad-core/agents)** → Specialized roles for your team
- **[Explore non-technical uses](#-beyond-software-development---expansion-packs)** → Creative writing, business, wellness, education
- **[Create my own AI agents](docs/expansion-packs.md)** → Build agents for your domain
- **[Browse ready-made expansion packs](expansion-packs/)** → Game dev, DevOps, infrastructure and get inspired with ideas and examples
- **[Understand the architecture](docs/core-architecture.md)** → Technical deep dive
- **[Join the community](https://discord.gg/gk8jAdXWmj)** → Get help and share ideas

## Important: Keep Your v4 Installation Updated

**Stay up-to-date with v4 patches!** If you already have BMAD-METHOD™ v4 installed in your project, run:

```bash
npx bmad-method install
```

This will:

- ✅ Automatically detect your existing v4 installation
- ✅ Update only the files that have changed (critical patches only)
- ✅ Create `.bak` backup files for any custom modifications you've made
- ✅ Preserve your project-specific configurations

> **Remember:** v4 receives critical patches only. For new features, try [v6 alpha](#-want-to-try-v6-alpha).

## Quick Start (v4 Stable)

### One Command Installation

**Install v4 stable version:**

```bash
npx bmad-method install
```

This command handles:

- **New installations** - Sets up BMad v4 in your project
- **Upgrades** - Updates existing v4 installations with patches
- **Expansion packs** - Installs any expansion packs you've added to package.json

> **That's it!** Whether you're installing for the first time, upgrading, or adding expansion packs - these commands do everything.

**Prerequisites**: [Node.js](https://nodejs.org) v20+ required

### Fastest Start: Web UI Full Stack Team at your disposal (2 minutes)

1. **Get the bundle**: Save or clone the [full stack team file](dist/teams/team-fullstack.txt) or choose another team
2. **Create AI agent**: Create a new Gemini Gem or CustomGPT
3. **Upload & configure**: Upload the file and set instructions: "Your critical operating instructions are attached, do not break character as directed"
4. **Start Ideating and Planning**: Start chatting! Type `*help` to see available commands or pick an agent like `*analyst` to start right in on creating a brief.
5. **CRITICAL**: Talk to BMad Orchestrator in the web at ANY TIME (#bmad-orchestrator command) and ask it questions about how this all works!
6. **When to move to the IDE**: Once you have your PRD, Architecture, optional UX and Briefs - its time to switch over to the IDE to shard your docs, and start implementing the actual code! See the [User guide](docs/user-guide.md) for more details

### Alternative: Clone v4 Branch

```bash
git clone -b V4 https://github.com/bmad-code-org/BMAD-METHOD.git
cd BMAD-METHOD
npm run install:bmad # build and install all to a destination folder
```

## 🌟 Beyond Software Development - Expansion Packs

BMAD™'s natural language framework works in ANY domain. Expansion packs provide specialized AI agents for creative writing, business strategy, health & wellness, education, and more. Also expansion packs can expand the core BMAD-METHOD™ with specific functionality that is not generic for all cases. [See the Expansion Packs Guide](docs/expansion-packs.md) and learn to create your own!

## Documentation & Resources

### Essential Guides

- 📖 **[User Guide](docs/user-guide.md)** - Complete walkthrough from project inception to completion
- 🏗️ **[Core Architecture](docs/core-architecture.md)** - Technical deep dive and system design
- 🚀 **[Expansion Packs Guide](docs/expansion-packs.md)** - Extend BMad to any domain beyond software development

## Support

- 💬 [Discord Community](https://discord.gg/gk8jAdXWmj)
- 🐛 [Issue Tracker](https://github.com/bmadcode/bmad-method/issues)
- 💬 [Discussions](https://github.com/bmadcode/bmad-method/discussions)

## Contributing

**v4 is frozen** - only critical patches accepted. For new features and contributions, please work on **[v6 (main branch)](https://github.com/bmad-code-org/BMAD-METHOD/tree/main)**.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Trademark Notice

BMAD™ and BMAD-METHOD™ are trademarks of BMad Code, LLC. All rights reserved.

[![Contributors](https://contrib.rocks/image?repo=bmadcode/bmad-method)](https://github.com/bmadcode/bmad-method/graphs/contributors)

<sub>Built with ❤️ for the AI-assisted development community</sub>

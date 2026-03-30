# Integrated Dashboard Chat — Design Spec

## Problem

The simulation dashboard and chat are separate pages. To talk with an agent you leave the dashboard, losing visibility on simulation state, events, and other agents. Switching between agents requires navigating back and forth. The group chat is another separate page entirely.

## Solution

Merge everything into a single-page simulation dashboard with three sections: agents list (left), activity feed (center), and chat panel (right). Clicking an agent opens their chat in the right panel without page navigation. A "Group" tab switches to group chat in the same panel.

## Layout

```
+------------------+-------------------+--------------------+
| STATUS BAR (tick, status, agents count, stability, cost)  |
+------------------+-------------------+--------------------+
|   AGENTS (left)  | ACTIVITY (center) |  CHAT (right)      |
|                  |                   |                    |
| [Lucrezia] ██░   | Tick 47: Marco    | [1:1] [Group]      |
| [Cesare]   ███   |   decided to...   | ─────────────────  |
| [Papa]     █░░   | Event: Storm...   | Lucrezia Borgia    |
| [Marco]    ████  |                   | Health ████░ 0.8   |
|                  |                   | Mood  ███░░ 0.6    |
| Selected agent   |                   |                    |
| highlighted with |                   | L: Buongiorno 10:23|
| indigo border    |                   | You: Ciao!    10:24|
|                  |                   | L: Come stai  10:24|
|                  |                   |                    |
|                  |                   | [________] [Send]  |
|                  |                   | Kick|Hug|Gift|...  |
+------------------+-------------------+--------------------+
|              INJECT EVENT (full width, collapsible)       |
+----------------------------------------------------------+
```

## Chat Panel Features

### Agent Header
- Agent name and role
- Live health bar (color-coded: green > yellow > red)
- Live mood bar (color-coded: blue > yellow > red)
- Wealth display
- Alive/Dead badge

### Message Bubbles
- User messages: right-aligned, indigo background
- Agent messages: left-aligned, gray background, with colored initial circle (first letter of name)
- Timestamp (HH:MM) in small text at bottom-right of each bubble, low opacity
- System messages: centered, gray italic

### Typing Indicator
- Three pulsing dots in a gray bubble, WhatsApp-style
- Shows while waiting for agent response
- Replaces the current "X is thinking..." text

### Quick Actions
- Row of small colored buttons below input: Kick, Punch, Spit, Threaten (red) | Hug, Pat, Gift, Drink (green) | God mode (purple)
- Same as current chat.html

### Tab Switching
- Two tabs at top of chat panel: "1:1" and "Group"
- 1:1 tab: chat with selected agent
- Group tab: shows agent selection checkboxes + group chat messages
- Switching tabs preserves state (messages stay)

### File Attachment
- Paperclip button next to input (same as current)

## Interaction Flow

1. Page loads: chat panel shows "Select an agent to start chatting" placeholder
2. User clicks an agent in the left column: panel loads that agent's chat history via AJAX, highlights the agent
3. User types and sends: message posted via fetch, agent response appears with typing indicator
4. User clicks another agent: panel switches to new agent's chat (previous chat preserved in memory)
5. User clicks "Group" tab: panel switches to group chat mode with agent selection
6. Live polling updates agent health/mood bars in both the left column AND the chat header simultaneously

## Technical Approach

- All in Alpine.js, no new dependencies
- Chat panel is a component within simulation_detail.html (not a separate page)
- Chat API endpoint stays the same (/simulations/{id}/chat/{agent_id}/)
- Messages loaded via fetch on agent selection
- Agent stats updated via the existing polling mechanism (fetchFeed)
- Separate chat.html and group_chat.html pages kept as-is for backward compatibility but no longer linked from main navigation

## What This Does NOT Change

- Backend views and API endpoints stay the same
- Chat message storage model stays the same
- LLM integration stays the same
- Event injection stays the same (just moves into the integrated page)

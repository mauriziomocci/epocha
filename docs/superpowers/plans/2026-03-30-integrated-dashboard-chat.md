# Integrated Dashboard Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the simulation dashboard and chat into a single page with a 3-column layout: agents list, activity feed, and integrated chat panel with 1:1/group tabs.

**Architecture:** Rewrite `simulation_detail.html` to include a right-side chat panel managed by Alpine.js. Add a lightweight AJAX endpoint to fetch chat history for any agent. The existing `chat_view` POST handler is reused for sending messages. Standalone chat pages remain for backward compatibility.

**Tech Stack:** Alpine.js, Tailwind CSS (via CDN), Django views, existing chat API

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `epocha/apps/dashboard/views.py` | Modify | Add `chat_history_api` endpoint, add `chat_send_api` endpoint |
| `epocha/apps/dashboard/urls.py` | Modify | Register new API endpoints |
| `epocha/apps/dashboard/templates/dashboard/simulation_detail.html` | Rewrite | 3-column layout with integrated chat panel |

---

## Task 1: Backend — Chat History and Send API Endpoints

Add two AJAX endpoints: one to fetch chat history for an agent, one to send a message. These are lightweight wrappers around existing logic, separated from the page-rendering views.

**Files:**
- Modify: `epocha/apps/dashboard/views.py`
- Modify: `epocha/apps/dashboard/urls.py`

- [ ] **Step 1: Add `chat_history_api` view**

Add this view to `epocha/apps/dashboard/views.py` (after the existing `chat_view` function):

```python
@login_required(login_url="/login/")
def chat_history_api(request, sim_id, agent_id):
    """Return chat history for an agent as JSON.

    Used by the integrated dashboard chat panel to load messages
    when the user selects an agent, without a full page reload.
    """
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    agent = get_object_or_404(Agent, id=agent_id, simulation=simulation)

    from epocha.apps.chat.models import ChatMessage, ChatSession

    session, _ = ChatSession.objects.get_or_create(
        simulation=simulation, user=request.user, agent=agent,
    )

    messages = [
        {
            "role": m.role,
            "content": m.content,
            "time": m.created_at.strftime("%H:%M"),
        }
        for m in ChatMessage.objects.filter(session=session).order_by("created_at")
    ]

    return JsonResponse({"messages": messages})
```

- [ ] **Step 2: Add `chat_send_api` view**

Add this view to `epocha/apps/dashboard/views.py`. This is the POST handler extracted from `chat_view`, accepting JSON with `message` field and returning the agent response as JSON. It reuses all existing chat logic (personality prompt, memories, events, mood effects):

```python
@login_required(login_url="/login/")
def chat_send_api(request, sim_id, agent_id):
    """Send a message to an agent and return the response as JSON.

    Used by the integrated dashboard chat panel. Handles the same
    logic as chat_view POST but without page rendering concerns.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    agent = get_object_or_404(Agent, id=agent_id, simulation=simulation)

    from epocha.apps.chat.models import ChatMessage, ChatSession

    session, _ = ChatSession.objects.get_or_create(
        simulation=simulation, user=request.user, agent=agent,
    )

    data = json.loads(request.body)
    message = data.get("message", "").strip()

    if not message:
        return JsonResponse({"role": "system", "content": "Empty message.", "time": ""})

    # Check if agent is dead
    agent.refresh_from_db()
    if not agent.is_alive:
        return JsonResponse({
            "role": "system",
            "content": f"{agent.name} is dead and cannot respond.",
            "time": "",
        })

    # Save user message
    ChatMessage.objects.create(
        session=session, role="user", content=message,
        tick_at=simulation.current_tick,
    )

    from epocha.apps.agents.memory import get_relevant_memories
    from epocha.apps.agents.personality import build_personality_prompt
    from epocha.apps.llm_adapter.client import get_chat_llm_client
    from epocha.apps.simulation.models import Event

    client = get_chat_llm_client()
    personality_prompt = build_personality_prompt(agent.personality)
    memories = get_relevant_memories(agent, current_tick=simulation.current_tick)
    memory_text = ""
    if memories:
        memory_text = "\n\nYour recent memories:\n" + "\n".join(f"- {m.content}" for m in memories[:5])

    # Recent events
    recent_events = list(Event.objects.filter(simulation=simulation).order_by("-id")[:3])
    events_context = ""
    if recent_events:
        events_context = (
            "\n\n[CONTEXT: " + " ".join(
                f"{e.title} - {e.description}" for e in reversed(recent_events)
            ) + f" — React to this as {agent.name}.]"
        )

    # Chat history (truncated)
    _MAX_USER_MSG_LENGTH = 200
    _MAX_AGENT_MSG_LENGTH = 50
    recent_chat = ChatMessage.objects.filter(session=session).order_by("-created_at")[:6]
    chat_history = ""
    if recent_chat.count() > 1:
        msgs = list(reversed(recent_chat))
        lines = []
        for m in msgs[:-1]:
            if m.role == "user":
                text = m.content[:_MAX_USER_MSG_LENGTH]
                if len(m.content) > _MAX_USER_MSG_LENGTH:
                    text += "..."
                lines.append(f"Visitor: {text}")
            else:
                text = m.content[:_MAX_AGENT_MSG_LENGTH]
                if len(m.content) > _MAX_AGENT_MSG_LENGTH:
                    text += "..."
                lines.append(f"You said: {text}")
        chat_history = "\n\nPrevious conversation:\n" + "\n".join(lines)

    system_prompt = (
        f"You are {agent.name}, a {agent.role}. "
        f"You are in a face-to-face conversation. Respond in character, 2-4 sentences. "
        f"IMPORTANT: {_get_language_instruction(request)}"
        f"React like a REAL HUMAN BEING would. The visitor can say anything or do anything:\n"
        f"- Physical actions: kick, punch, hug, caress, kiss, stab, shoot, etc.\n"
        f"- Emotional: insults, compliments, jokes, flirting, threats, declarations of love.\n"
        f"- Social: gifts, proposals, questions, gossip, lies, confessions.\n"
        f"React naturally based on what was done: violence causes pain and anger, "
        f"kindness causes warmth, jokes cause laughter, insults cause offense, "
        f"flirting causes embarrassment or interest, etc. "
        f"Match the intensity of your reaction to the action.\n"
        f"CRITICAL: Focus ONLY on the visitor's LATEST message. "
        f"Do NOT repeat or reference previous reactions. "
        f"If the visitor changes topic or tone, adapt immediately.\n\n"
        f"{personality_prompt}"
        f"{memory_text}{chat_history}"
    )

    prompt_with_hint = f"{message}{events_context} /no_think"

    try:
        response = client.complete(
            prompt=prompt_with_hint,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=500,
            simulation_id=simulation.id,
        )
    except Exception:
        response = "*remains silent, looking confused*"

    _apply_chat_mood_effects(agent, message)

    ChatMessage.objects.create(
        session=session, role="agent", content=response,
        tick_at=simulation.current_tick,
    )

    from django.utils import timezone

    return JsonResponse({
        "role": "agent",
        "content": response,
        "time": timezone.now().strftime("%H:%M"),
    })
```

- [ ] **Step 3: Register the new URL patterns**

Add two new paths to `epocha/apps/dashboard/urls.py`, before the existing chat path:

```python
    path("simulations/<int:sim_id>/chat/<int:agent_id>/history/", views.chat_history_api, name="chat-history-api"),
    path("simulations/<int:sim_id>/chat/<int:agent_id>/send/", views.chat_send_api, name="chat-send-api"),
```

- [ ] **Step 4: Run full test suite**

Run: `pytest --cov=epocha -v`
Expected: All tests PASS (no test changes needed -- new endpoints are additive)

- [ ] **Step 5: Commit**

```
feat(dashboard): add chat history and send API endpoints

CHANGE: Add /chat/{agent_id}/history/ and /chat/{agent_id}/send/
endpoints for the integrated dashboard chat panel. These are
lightweight JSON APIs that reuse existing chat logic without
page rendering.
```

---

## Task 2: Rewrite Simulation Detail Template with Integrated Chat

Replace the 2-column simulation_detail.html with a 3-column layout that includes the chat panel.

**Files:**
- Rewrite: `epocha/apps/dashboard/templates/dashboard/simulation_detail.html`

- [ ] **Step 1: Rewrite the template**

Replace the entire contents of `epocha/apps/dashboard/templates/dashboard/simulation_detail.html` with the new 3-column layout. The template must include:

**Structure:**
- Status bar (top, full width): tick, status, agents count, stability, LLM cost — same as current
- Three columns below: agents list (left ~25%), activity feed (center ~35%), chat panel (right ~40%)
- Inject Event section (bottom, full width, collapsible) — same as current

**Left column (Agents):**
- Same agent cards as current (name, role, health bar, mood bar, wealth)
- Click an agent: sets `selectedAgentId` in Alpine state, triggers chat load
- Selected agent highlighted with indigo border
- Dead agents grayed out

**Center column (Activity):**
- Same as current: events + decisions feed with live polling

**Right column (Chat Panel):**
- Two tabs at top: "1:1" and "Group"
- **1:1 tab** (default):
  - Agent header: name, role, health/mood bars (updated from liveAgents), alive/dead badge
  - Chat messages area (scrollable):
    - User messages: right-aligned, indigo bg
    - Agent messages: left-aligned, gray bg, with colored initial circle
    - Timestamp (HH:MM) small at bottom-right of each bubble, opacity-40
    - System messages: centered, italic
  - Typing indicator: three pulsing dots in gray bubble (shown during loading)
  - Quick actions row: Kick, Punch, Spit, Threaten (red) | Hug, Pat, Gift, Drink (green) | God mode (purple)
  - Input row: text input + send button
  - Placeholder when no agent selected: "Select an agent to start chatting"
- **Group tab:**
  - Agent checkboxes for selecting participants
  - Same chat area but with colored agent names
  - Input row

**Alpine.js data model additions:**
```javascript
// Chat state
selectedAgentId: null,
selectedAgentName: '',
selectedAgentRole: '',
chatMessages: [],
chatLoading: false,
chatInput: '',
chatTab: 'single',  // 'single' or 'group'
groupMessages: [],
groupLoading: false,
groupInput: '',
groupSelectedAgents: [],  // all agent IDs by default
chatMsgCounter: 0,
```

**Key methods:**
```javascript
async selectAgent(agentId, agentName, agentRole) {
    this.selectedAgentId = agentId;
    this.selectedAgentName = agentName;
    this.selectedAgentRole = agentRole;
    this.chatTab = 'single';
    // Load chat history
    const r = await fetch(`/simulations/{{ simulation.id }}/chat/${agentId}/history/`);
    const data = await r.json();
    this.chatMsgCounter = 0;
    this.chatMessages = data.messages.map(m => ({
        id: ++this.chatMsgCounter, role: m.role, content: m.content, time: m.time
    }));
    this.$nextTick(() => this.scrollChat());
},

async sendChat() {
    if (!this.chatInput.trim() || this.chatLoading || !this.selectedAgentId) return;
    const msg = this.chatInput.trim();
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
    this.chatMessages.push({ id: ++this.chatMsgCounter, role: 'user', content: msg, time: timeStr });
    this.chatInput = '';
    this.chatLoading = true;
    this.scrollChat();
    try {
        const r = await fetch(`/simulations/{{ simulation.id }}/chat/${this.selectedAgentId}/send/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
            body: JSON.stringify({ message: msg }),
        });
        const data = await r.json();
        this.chatMessages.push({ id: ++this.chatMsgCounter, role: data.role, content: data.content, time: data.time || timeStr });
    } catch (e) {
        this.chatMessages.push({ id: ++this.chatMsgCounter, role: 'system', content: 'Error: Could not reach the agent.', time: '' });
    }
    this.chatLoading = false;
    this.scrollChat();
},

quickAction(text) {
    this.chatInput = text;
    this.sendChat();
},

async sendGroupChat() {
    if (!this.groupInput.trim() || this.groupLoading || !this.groupSelectedAgents.length) return;
    const msg = this.groupInput.trim();
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
    this.groupMessages.push({ id: ++this.chatMsgCounter, role: 'user', content: msg, time: timeStr });
    this.groupInput = '';
    this.groupLoading = true;
    this.scrollChat();
    try {
        const r = await fetch('/simulations/{{ simulation.id }}/group-chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ message: msg, agent_ids: this.groupSelectedAgents }),
        });
        const data = await r.json();
        for (const resp of data.responses) {
            this.groupMessages.push({
                id: ++this.chatMsgCounter, role: 'agent',
                agent_name: resp.agent_name, agent_role: resp.agent_role,
                content: resp.content, time: timeStr,
            });
        }
    } catch (e) {
        this.groupMessages.push({ id: ++this.chatMsgCounter, role: 'system', content: 'Error reaching agents.', time: '' });
    }
    this.groupLoading = false;
    this.scrollChat();
},

toggleGroupAgent(id) {
    const idx = this.groupSelectedAgents.indexOf(id);
    if (idx >= 0) this.groupSelectedAgents.splice(idx, 1);
    else this.groupSelectedAgents.push(id);
},

scrollChat() {
    this.$nextTick(() => {
        const el = document.getElementById('chat-panel-messages');
        if (el) el.scrollTop = el.scrollHeight;
    });
},

getSelectedAgent() {
    return this.liveAgents.find(a => a.id === this.selectedAgentId) || null;
},

getAgentInitialColor(name) {
    const colors = ['bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-pink-500', 'bg-purple-500', 'bg-cyan-500', 'bg-orange-500', 'bg-red-500'];
    if (!this._colorMap) this._colorMap = {};
    if (!this._colorMap[name]) this._colorMap[name] = colors[Object.keys(this._colorMap).length % colors.length];
    return this._colorMap[name];
},
```

**Typing indicator CSS** (add to template as inline style):
```css
.typing-dots span {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #9ca3af;
    animation: typing 1.4s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
    0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
    30% { opacity: 1; transform: translateY(-4px); }
}
```

- [ ] **Step 2: Verify page loads and basic interaction works**

Start the Docker containers and open http://localhost:8000/simulations/1/ in a browser.
Verify:
- 3-column layout renders correctly
- Clicking an agent loads chat history in the right panel
- Sending a message works and response appears
- Group chat tab works
- Live polling still updates agent stats and activity feed
- Quick actions work
- Inject event section still works

- [ ] **Step 3: Run full test suite**

Run: `pytest --cov=epocha -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```
feat(dashboard): integrated 3-column layout with chat panel

CHANGE: Rewrite simulation detail page as 3-column layout: agents
list (left), activity feed (center), chat panel (right). Chat with
any agent by clicking their name -- no page navigation needed.
Group chat available as a tab. Typing indicator with pulsing dots,
colored agent initials, message timestamps, and live health/mood
bars in the chat header.
```

---

## Summary

| Task | What it builds |
|------|---------------|
| 1 | Backend: chat history + send API endpoints |
| 2 | Frontend: 3-column simulation_detail.html with integrated chat |

After completion:
- Single-page dashboard with chat, no more navigating between pages
- Click agent = instant chat in right panel
- Group chat as tab in same panel
- Live stats update everywhere simultaneously
- Typing indicator with pulsing dots
- Colored initials and timestamps on messages
- Quick actions row for physical/social interactions

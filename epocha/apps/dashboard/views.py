"""Dashboard views — server-rendered UI for testing and demos.

Uses Django templates with Alpine.js for interactivity and Tailwind CSS
via CDN for styling. No build step required.
"""
from __future__ import annotations

import json
import random

from django.contrib import messages as django_messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from epocha.apps.agents.models import Agent, DecisionLog
from epocha.apps.llm_adapter.models import LLMRequest
from epocha.apps.simulation.models import Event, Simulation
from epocha.apps.users.models import User
from epocha.apps.world.models import World


# ---------- Auth ----------

def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "")
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        errors = []
        if not email or not username or not password:
            errors.append("All fields are required.")
        if password != password_confirm:
            errors.append("Passwords do not match.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if User.objects.filter(email=email).exists():
            errors.append("Email already registered.")

        if errors:
            return render(request, "dashboard/register.html", {"errors": errors})

        user = User.objects.create_user(email=email, username=username, password=password)
        login(request, user)
        return redirect("dashboard:home")

    return render(request, "dashboard/register.html")


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            return redirect("dashboard:home")
        return render(request, "dashboard/login.html", {"error": "Invalid credentials."})

    return render(request, "dashboard/login.html")


def logout_view(request):
    logout(request)
    return redirect("dashboard:login")


# ---------- Simulations ----------

@login_required(login_url="/login/")
def simulation_list_view(request):
    simulations = Simulation.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "dashboard/simulation_list.html", {"simulations": simulations})


@login_required(login_url="/login/")
def simulation_create_view(request):
    if request.method == "POST":
        prompt = request.POST.get("prompt", "")
        if not prompt.strip():
            return render(request, "dashboard/simulation_create.html", {"error": "Prompt is required."})

        simulation = Simulation.objects.create(
            name="Express Simulation",
            description=prompt[:500],
            seed=random.randint(0, 2**32),
            status=Simulation.Status.INITIALIZING,
            owner=request.user,
        )

        try:
            from epocha.apps.world.generator import generate_world_from_prompt

            result = generate_world_from_prompt(prompt=prompt, simulation=simulation)
            simulation.status = Simulation.Status.PAUSED
            simulation.save(update_fields=["status"])
            return redirect("dashboard:simulation-detail", sim_id=simulation.id)
        except Exception as e:
            simulation.status = Simulation.Status.ERROR
            simulation.save(update_fields=["status"])
            return render(request, "dashboard/simulation_create.html", {"error": str(e)})

    return render(request, "dashboard/simulation_create.html")


@login_required(login_url="/login/")
def simulation_detail_view(request, sim_id):
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    agents = Agent.objects.filter(simulation=simulation).order_by("name")
    events = Event.objects.filter(simulation=simulation).order_by("-tick")[:50]
    # Show agent decisions as activity feed (DecisionLog is populated every tick)
    decisions = (
        DecisionLog.objects.filter(simulation=simulation)
        .select_related("agent")
        .order_by("-tick")[:30]
    )
    world = World.objects.filter(simulation=simulation).first()

    # Cost summary
    from django.db.models import Count, Sum

    cost_stats = LLMRequest.objects.filter(
        simulation_id=simulation.id, success=True,
    ).aggregate(
        total_cost=Sum("cost_usd"),
        total_requests=Count("id"),
    )

    context = {
        "simulation": simulation,
        "agents": agents,
        "events": events,
        "decisions": decisions,
        "world": world,
        "total_cost": round(cost_stats["total_cost"] or 0, 4),
        "total_requests": cost_stats["total_requests"] or 0,
    }
    return render(request, "dashboard/simulation_detail.html", context)


@login_required(login_url="/login/")
@require_POST
def simulation_play_view(request, sim_id):
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    simulation.status = Simulation.Status.RUNNING
    simulation.save(update_fields=["status"])

    from epocha.apps.simulation.tasks import run_simulation_loop

    run_simulation_loop.delay(simulation.id)
    return redirect("dashboard:simulation-detail", sim_id=simulation.id)


@login_required(login_url="/login/")
@require_POST
def simulation_pause_view(request, sim_id):
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    simulation.status = Simulation.Status.PAUSED
    simulation.save(update_fields=["status"])
    return redirect("dashboard:simulation-detail", sim_id=simulation.id)


@login_required(login_url="/login/")
@require_POST
def inject_event_view(request, sim_id):
    """Inject a user-defined event into the simulation.

    The event is saved to the Event model and will be included in the
    context of all agent decisions for the next 5 ticks, causing agents
    to react to it according to their personality.
    """
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)

    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    event_type = request.POST.get("event_type", "custom")
    severity = float(request.POST.get("severity", "0.5"))

    if not title or not description:
        return redirect("dashboard:simulation-detail", sim_id=simulation.id)

    Event.objects.create(
        simulation=simulation,
        tick=simulation.current_tick,
        event_type=event_type,
        title=title,
        description=description,
        severity=min(1.0, max(0.0, severity)),
        caused_by="user_injection",
    )

    django_messages.success(request, f"Event injected: {title}")

    # Redirect back to the referring page (chat or simulation detail)
    referer = request.META.get("HTTP_REFERER", "")
    if referer and ("/chat/" in referer or "/group-chat/" in referer):
        return redirect(referer)
    return redirect("dashboard:simulation-detail", sim_id=simulation.id)


@login_required(login_url="/login/")
def simulation_report_view(request, sim_id):
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)

    if not simulation.report:
        from epocha.apps.simulation.report import generate_simulation_report

        generate_simulation_report(simulation)
        simulation.refresh_from_db()

    return render(request, "dashboard/simulation_report.html", {"simulation": simulation})


@login_required(login_url="/login/")
def chat_view(request, sim_id, agent_id):
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    agent = get_object_or_404(Agent, id=agent_id, simulation=simulation)

    from epocha.apps.chat.models import ChatMessage, ChatSession

    # Get or create chat session
    session, _ = ChatSession.objects.get_or_create(
        simulation=simulation, user=request.user, agent=agent,
    )

    # Handle AJAX chat messages (JSON or FormData with file)
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # Parse message and optional file from request
        if request.content_type and "multipart" in request.content_type:
            message = request.POST.get("message", "")
            uploaded_file = request.FILES.get("file")
        else:
            data = json.loads(request.body)
            message = data.get("message", "")
            uploaded_file = None

        # Extract text from uploaded file
        file_context = ""
        if uploaded_file:
            import tempfile

            from epocha.apps.world.document_parser import SUPPORTED_EXTENSIONS, extract_text

            suffix = f".{uploaded_file.name.rsplit('.', 1)[-1]}" if "." in uploaded_file.name else ""
            if suffix.lower() in SUPPORTED_EXTENSIONS:
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    for chunk in uploaded_file.chunks():
                        tmp.write(chunk)
                    tmp.flush()
                    extracted = extract_text(tmp.name)
                    file_context = f"\n\n[The visitor hands you a document titled '{uploaded_file.name}'. Its content is:]\n{extracted[:2000]}"
            elif suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                file_context = f"\n\n[The visitor shows you an image: {uploaded_file.name}. React to it based on the conversation context.]"
            else:
                file_context = f"\n\n[The visitor shows you a file: {uploaded_file.name}]"

        if message.strip() or file_context:
            # Save user message (include file reference if any)
            save_content = message
            if uploaded_file:
                save_content += f" [Attached: {uploaded_file.name}]"
            ChatMessage.objects.create(
                session=session, role="user", content=save_content,
                tick_at=simulation.current_tick,
            )

            from epocha.apps.agents.memory import get_relevant_memories
            from epocha.apps.agents.personality import build_personality_prompt
            from epocha.apps.llm_adapter.client import get_llm_client

            client = get_llm_client()
            personality_prompt = build_personality_prompt(agent.personality)
            memories = get_relevant_memories(agent, current_tick=simulation.current_tick)
            memory_text = ""
            if memories:
                memory_text = "\n\nYour recent memories:\n" + "\n".join(f"- {m.content}" for m in memories[:5])

            # Include recent events (injected by user) so the agent knows what happened
            recent_events = list(Event.objects.filter(simulation=simulation).order_by("-tick")[:5])
            events_text = ""
            if recent_events:
                events_text = (
                    "\n\n*** CRITICAL: THESE EVENTS HAPPENED TO YOU AND AFFECT YOU NOW ***\n"
                    + "\n".join(f"- {e.title}: {e.description}" for e in recent_events)
                    + f"\nYou ({agent.name}) are directly affected by these events. "
                    "React emotionally and physically. Show pain, fear, anger, or distress as appropriate. "
                    "Do NOT pretend everything is fine if something bad happened to you."
                )
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("CHAT CONTEXT for %s: events=%d, events_text_len=%d", agent.name, len(recent_events), len(events_text))

            # Include recent chat history for continuity
            recent_chat = ChatMessage.objects.filter(session=session).order_by("-created_at")[:10]
            chat_history = ""
            if recent_chat.count() > 1:
                msgs = list(reversed(recent_chat))
                chat_history = "\n\nPrevious conversation:\n" + "\n".join(
                    f"{'Visitor' if m.role == 'user' else agent.name}: {m.content}" for m in msgs[:-1]
                )

            system_prompt = (
                f"You are {agent.name}, a {agent.role}. "
                f"Someone is talking to you. Respond in character, briefly and naturally. "
                f"Keep your response to 2-3 sentences maximum."
                f"{events_text}\n\n"
                f"{personality_prompt}"
                f"{memory_text}{chat_history}"
            )

            prompt_with_hint = f"{message}{file_context} /no_think"

            response = client.complete(
                prompt=prompt_with_hint,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=150,
                simulation_id=simulation.id,
            )

            # Save agent response
            ChatMessage.objects.create(
                session=session, role="agent", content=response,
                tick_at=simulation.current_tick,
            )

            return JsonResponse({"role": "agent", "content": response})

        return JsonResponse({"role": "system", "content": "Empty message."})

    # Load chat history for initial page render
    chat_history = list(
        ChatMessage.objects.filter(session=session)
        .order_by("created_at")
        .values("role", "content")
    )

    return render(request, "dashboard/chat.html", {
        "simulation": simulation,
        "agent": agent,
        "chat_history_json": json.dumps(chat_history),
    })


@login_required(login_url="/login/")
def group_chat_view(request, sim_id):
    """Group chat: user talks with multiple agents at once.

    Each agent responds in sequence, seeing what previous agents said.
    This creates natural group dynamics — agreements, disagreements,
    alliances forming in real-time conversation.
    """
    simulation = get_object_or_404(Simulation, id=sim_id, owner=request.user)
    all_agents = Agent.objects.filter(simulation=simulation, is_alive=True).order_by("name")

    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        data = json.loads(request.body)
        message = data.get("message", "").strip()
        agent_ids = data.get("agent_ids", [])

        if not message or not agent_ids:
            return JsonResponse({"responses": []})

        from epocha.apps.agents.memory import get_relevant_memories
        from epocha.apps.agents.personality import build_personality_prompt
        from epocha.apps.llm_adapter.client import get_llm_client

        client = get_llm_client()
        agents = Agent.objects.filter(id__in=agent_ids, simulation=simulation, is_alive=True)

        # Gather recent events
        recent_events = Event.objects.filter(
            simulation=simulation,
            tick__gte=max(0, simulation.current_tick - 10),
        ).order_by("-tick")[:5]
        events_text = ""
        if recent_events:
            events_text = "\nRecent events: " + "; ".join(f"{e.title}" for e in recent_events)

        responses = []
        conversation_so_far = f"Visitor: {message}"

        for agent in agents:
            personality_prompt = build_personality_prompt(agent.personality)
            memories = get_relevant_memories(agent, current_tick=simulation.current_tick)
            memory_text = ""
            if memories:
                memory_text = "\nYour memories: " + "; ".join(m.content for m in memories[:3])

            system_prompt = (
                f"{personality_prompt}\n\n"
                f"You are {agent.name}, a {agent.role}. "
                f"You are in a group conversation. Respond in character, briefly (1-2 sentences). "
                f"React to what others said.{events_text}{memory_text}"
            )

            try:
                response = client.complete(
                    prompt=f"{conversation_so_far} /no_think",
                    system_prompt=system_prompt,
                    temperature=0.8,
                    max_tokens=100,
                    simulation_id=simulation.id,
                )
            except Exception:
                response = "*remains silent*"

            responses.append({"agent_name": agent.name, "agent_role": agent.role, "content": response})
            conversation_so_far += f"\n{agent.name}: {response}"

        return JsonResponse({"responses": responses})

    return render(request, "dashboard/group_chat.html", {
        "simulation": simulation,
        "agents": all_agents,
    })

"""Dashboard views — server-rendered UI for testing and demos.

Uses Django templates with Alpine.js for interactivity and Tailwind CSS
via CDN for styling. No build step required.
"""
from __future__ import annotations

import json
import random

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

    # Handle AJAX chat messages
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        message = json.loads(request.body).get("message", "")
        if message.strip():
            from epocha.apps.agents.memory import get_relevant_memories
            from epocha.apps.agents.personality import build_personality_prompt
            from epocha.apps.llm_adapter.client import get_llm_client

            client = get_llm_client()
            personality_prompt = build_personality_prompt(agent.personality)
            memories = get_relevant_memories(agent, current_tick=simulation.current_tick)
            memory_text = ""
            if memories:
                memory_text = "\n\nYour recent memories:\n" + "\n".join(f"- {m.content}" for m in memories[:5])

            system_prompt = (
                f"{personality_prompt}\n\n"
                f"You are {agent.name}, a {agent.role}. "
                f"Someone is talking to you. Respond in character, briefly and naturally. "
                f"Keep your response to 2-3 sentences maximum.{memory_text}"
            )

            # /no_think disables Qwen3's internal reasoning for faster responses
            prompt_with_hint = f"{message} /no_think"

            response = client.complete(
                prompt=prompt_with_hint,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=150,
                simulation_id=simulation.id,
            )
            return JsonResponse({"role": "agent", "content": response})

        return JsonResponse({"role": "system", "content": "Empty message."})

    return render(request, "dashboard/chat.html", {"simulation": simulation, "agent": agent})

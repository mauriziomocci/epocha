"""Context processors for the dashboard — available in all templates."""
from django.utils import timezone

from epocha.apps.llm_adapter.models import LLMRequest

# Groq free tier daily limit
DAILY_REQUEST_LIMIT = 14400

# Language configuration
LANGUAGES = {
    "en": {
        "name": "English",
        "instruction": "Respond in English.",
        "ui": {
            "status": "Status", "tick": "Tick", "agents": "Agents", "stability": "Stability",
            "llm_cost": "LLM Cost", "calls": "calls", "alive": "Alive", "dead": "Dead",
            "health": "Health", "mood": "Mood", "wealth": "Wealth",
            "live_activity": "Live Activity", "no_activity": "No activity yet. Press Play to start.",
            "inject_event": "Inject Event", "event_title": "Event title",
            "what_happens": "What happens...", "severity": "Severity",
            "select_agent": "Select an agent to start chatting",
            "say_something": "Say something to", "send": "Send",
            "group": "Group", "select_participants": "Select participants:",
            "select_all": "Select all", "say_to_group": "Say something to the group...",
            "back": "Back to simulations", "play": "Play", "pause": "Pause", "report": "Report",
            "targeting": "targeting",
        },
    },
    "it": {
        "name": "Italiano",
        "instruction": "Rispondi in italiano.",
        "ui": {
            "status": "Stato", "tick": "Turno", "agents": "Agenti", "stability": "Stabilita'",
            "llm_cost": "Costo LLM", "calls": "chiamate", "alive": "Vivo", "dead": "Morto",
            "health": "Salute", "mood": "Umore", "wealth": "Ricchezza",
            "live_activity": "Attivita' in tempo reale", "no_activity": "Nessuna attivita'. Premi Play per iniziare.",
            "inject_event": "Inietta Evento", "event_title": "Titolo evento",
            "what_happens": "Cosa succede...", "severity": "Gravita'",
            "select_agent": "Seleziona un agente per chattare",
            "say_something": "Scrivi qualcosa a", "send": "Invia",
            "group": "Gruppo", "select_participants": "Seleziona partecipanti:",
            "select_all": "Seleziona tutti", "say_to_group": "Scrivi qualcosa al gruppo...",
            "back": "Torna alle simulazioni", "play": "Avvia", "pause": "Pausa", "report": "Rapporto",
            "targeting": "verso",
        },
    },
    "fr": {
        "name": "Francais",
        "instruction": "Reponds en francais.",
        "ui": {
            "status": "Statut", "tick": "Tour", "agents": "Agents", "stability": "Stabilite",
            "llm_cost": "Cout LLM", "calls": "appels", "alive": "Vivant", "dead": "Mort",
            "health": "Sante", "mood": "Humeur", "wealth": "Richesse",
            "live_activity": "Activite en direct", "no_activity": "Aucune activite. Appuyez sur Play.",
            "inject_event": "Injecter Evenement", "event_title": "Titre",
            "what_happens": "Que se passe-t-il...", "severity": "Gravite",
            "select_agent": "Selectionnez un agent pour discuter",
            "say_something": "Dites quelque chose a", "send": "Envoyer",
            "group": "Groupe", "select_participants": "Selectionnez les participants:",
            "select_all": "Tout selectionner", "say_to_group": "Dites quelque chose au groupe...",
            "back": "Retour aux simulations", "play": "Jouer", "pause": "Pause", "report": "Rapport",
            "targeting": "ciblant",
        },
    },
    "de": {
        "name": "Deutsch",
        "instruction": "Antworte auf Deutsch.",
        "ui": {
            "status": "Status", "tick": "Runde", "agents": "Agenten", "stability": "Stabilitat",
            "llm_cost": "LLM-Kosten", "calls": "Aufrufe", "alive": "Lebendig", "dead": "Tot",
            "health": "Gesundheit", "mood": "Stimmung", "wealth": "Vermogen",
            "live_activity": "Live-Aktivitat", "no_activity": "Keine Aktivitat. Druecken Sie Play.",
            "inject_event": "Ereignis einfugen", "event_title": "Titel",
            "what_happens": "Was passiert...", "severity": "Schwere",
            "select_agent": "Agent zum Chatten auswahlen",
            "say_something": "Schreibe etwas an", "send": "Senden",
            "group": "Gruppe", "select_participants": "Teilnehmer auswahlen:",
            "select_all": "Alle auswahlen", "say_to_group": "Schreibe etwas an die Gruppe...",
            "back": "Zuruck zu Simulationen", "play": "Start", "pause": "Pause", "report": "Bericht",
            "targeting": "Ziel",
        },
    },
    "es": {
        "name": "Espanol",
        "instruction": "Responde en espanol.",
        "ui": {
            "status": "Estado", "tick": "Turno", "agents": "Agentes", "stability": "Estabilidad",
            "llm_cost": "Coste LLM", "calls": "llamadas", "alive": "Vivo", "dead": "Muerto",
            "health": "Salud", "mood": "Animo", "wealth": "Riqueza",
            "live_activity": "Actividad en vivo", "no_activity": "Sin actividad. Pulsa Play para empezar.",
            "inject_event": "Inyectar Evento", "event_title": "Titulo",
            "what_happens": "Que sucede...", "severity": "Gravedad",
            "select_agent": "Selecciona un agente para chatear",
            "say_something": "Escribe algo a", "send": "Enviar",
            "group": "Grupo", "select_participants": "Selecciona participantes:",
            "select_all": "Seleccionar todos", "say_to_group": "Escribe algo al grupo...",
            "back": "Volver a simulaciones", "play": "Iniciar", "pause": "Pausa", "report": "Informe",
            "targeting": "dirigido a",
        },
    },
}


def llm_quota(request):
    """Add today's LLM usage stats to every template context."""
    today = timezone.now().date()
    today_count = LLMRequest.objects.filter(
        created_at__date=today,
    ).count()

    # Language preference from session
    current_language = request.session.get("epocha_language", "en")
    language_instruction = LANGUAGES.get(current_language, LANGUAGES["en"])["instruction"]

    ui_labels = LANGUAGES.get(current_language, LANGUAGES["en"]).get("ui", LANGUAGES["en"]["ui"])

    return {
        "llm_today_count": today_count,
        "llm_daily_limit": DAILY_REQUEST_LIMIT,
        "llm_remaining": max(0, DAILY_REQUEST_LIMIT - today_count),
        "current_language": current_language,
        "language_instruction": language_instruction,
        "ui": ui_labels,
    }

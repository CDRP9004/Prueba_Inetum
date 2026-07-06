"""CLI de análisis del histórico de conversaciones: uso -> python -m analytics.run_report"""
from __future__ import annotations

from analytics.metrics import compute_summary


def main() -> None:
    summary = compute_summary()

    if summary.total_messages == 0:
        print("Todavía no hay conversaciones registradas.")
        return

    print("=== Resumen del histórico de conversaciones ===")
    print(f"Sesiones (conversaciones): {summary.total_sessions}")
    print(f"Mensajes totales: {summary.total_messages} "
          f"({summary.total_user_messages} de usuario, {summary.total_assistant_messages} del asistente)")
    print(f"Promedio de mensajes por sesión: {summary.avg_messages_per_session:.1f}")
    if summary.avg_latency_ms is not None:
        print(f"Latencia promedio de respuesta: {summary.avg_latency_ms:.0f} ms "
              f"(p95: {summary.p95_latency_ms:.0f} ms)")
    print(f"Rango de fechas: {summary.first_message_at} -> {summary.last_message_at}")

    print("\n=== Mensajes por día ===")
    for day, count in summary.messages_per_day.items():
        print(f"  {day}: {count}")

    print("\n=== Palabras/temas más frecuentes en preguntas de usuarios ===")
    for word, count in summary.top_keywords:
        print(f"  {word}: {count}")


if __name__ == "__main__":
    main()

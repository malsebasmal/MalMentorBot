import datetime
import logging
import os

import discord
import pytz
from discord.ext import commands, tasks
from dotenv import load_dotenv

import webserver

load_dotenv()

# --- Logging: esto es lo que te va a permitir ver en los logs de Render
# si el loop está corriendo, y qué excepción lo tumbó si vuelve a pasar.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("malmentorbot")

TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_ASISTENCIA_ID = int(os.getenv("CANAL_ASISTENCIA_ID"))
CANAL_RACHAS_ID = int(os.getenv("CANAL_RACHAS_ID"))
CANAL_PROGRESO_ID = int(os.getenv("CANAL_PROGRESO_ID"))
JOAQUIN_ID = int(os.getenv("JOAQUIN_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ZONA_HORARIA = "America/Lima"

intents = discord.Intents.default()

tareas_ejecutadas = set()


class MiBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        log.info("Comandos slash sincronizados")


client = MiBot()


@client.event
async def on_ready():
    log.info(f"Bot conectado como {client.user}")
    if not tarea_diaria.is_running():
        tarea_diaria.start()
        log.info("tarea_diaria iniciada")


@client.tree.command(name="ping", description="Verifica que el bot esté activo")
async def ping(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ No tenés permisos.", ephemeral=True)
        return

    zona = pytz.timezone(ZONA_HORARIA)
    ahora = datetime.datetime.now(zona)
    loop_status = "🟢 corriendo" if tarea_diaria.is_running() else "🔴 DETENIDA"
    await interaction.response.send_message(
        f"✅ **Bot activo**\n"
        f"🕐 Hora Lima: `{ahora.strftime('%d/%m/%Y %H:%M:%S')}`\n"
        f"🤖 Conectado como: `{client.user}`\n"
        f"🔁 Loop tarea_diaria: {loop_status}\n"
        f"📊 Iteración #{tarea_diaria.current_loop}",
        ephemeral=True
    )


@tasks.loop(minutes=1)
async def tarea_diaria():
    zona = pytz.timezone(ZONA_HORARIA)
    ahora = datetime.datetime.now(zona)
    es_laboral = ahora.weekday() <= 4
    es_viernes = ahora.weekday() == 4

    hora = ahora.hour
    minuto = ahora.minute
    hoy = ahora.strftime('%Y-%m-%d')

    # --- Asistencia ---
    clave_asistencia = f"asistencia_{hoy}"
    if es_laboral and hora == 8 and minuto <= 10 and clave_asistencia not in tareas_ejecutadas:
        try:
            tareas_ejecutadas.add(clave_asistencia)
            canal = client.get_channel(CANAL_ASISTENCIA_ID)
            if canal:
                mensaje = await canal.send(
                    f"📋 ¡Buenos días <@{JOAQUIN_ID}>!\n"
                    "Reaccioná con ✅ para confirmar tu asistencia de hoy."
                )
                await mensaje.add_reaction("✅")
                log.info(f"Mensaje de asistencia enviado ({hoy})")
            else:
                log.warning(f"No se encontró el canal de asistencia ({CANAL_ASISTENCIA_ID})")
        except Exception:
            log.exception("Error enviando mensaje de asistencia")

    # --- Rachas ---
    clave_racha = f"racha_{hoy}"
    if es_laboral and hora == 20 and minuto <= 10 and clave_racha not in tareas_ejecutadas:
        try:
            tareas_ejecutadas.add(clave_racha)
            canal = client.get_channel(CANAL_RACHAS_ID)
            if canal:
                mensaje = await canal.send(
                    f"🔥 <@{JOAQUIN_ID}> ¡Terminó la jornada de hoy!\n\n"
                    "Usá el comando `/profile` de LionBot acá abajo para mostrar "
                    "tus estadísticas del día y mantener la racha activa. 👇"
                )
                await mensaje.create_thread(
                    name=f"Stats {ahora.strftime('%d/%m/%Y')}",
                    auto_archive_duration=1440
                )
                log.info(f"Mensaje de racha enviado ({hoy})")
            else:
                log.warning(f"No se encontró el canal de rachas ({CANAL_RACHAS_ID})")
        except Exception:
            log.exception("Error enviando mensaje de racha")

    # --- Progreso semanal (viernes) ---
    clave_progreso = f"progreso_{hoy}"
    if es_viernes and hora == 20 and minuto <= 10 and clave_progreso not in tareas_ejecutadas:
        try:
            tareas_ejecutadas.add(clave_progreso)
            canal = client.get_channel(CANAL_PROGRESO_ID)
            if canal:
                mensaje = await canal.send(
                    f"📈 <@{JOAQUIN_ID}> ¡Terminó otra semana!\n\n"
                    "Es momento de reflexionar. Respondé en el hilo 👇\n\n"
                    "**1.** ¿Qué fue lo que más te costó esta semana?\n"
                    "**2.** ¿Cómo te autoevaluás del 1 al 10?\n"
                    "**3.** ¿Hay algún tema que sientas que necesitás repasar?"
                )
                hilo = await mensaje.create_thread(
                    name=f"Semana del {ahora.strftime('%d/%m/%Y')}",
                    auto_archive_duration=4320
                )
                await hilo.send(
                    f"<@{JOAQUIN_ID}> Respondé acá tu resumen de la semana 👆"
                )
                log.info(f"Mensaje de progreso semanal enviado ({hoy})")
            else:
                log.warning(f"No se encontró el canal de progreso ({CANAL_PROGRESO_ID})")
        except Exception:
            log.exception("Error enviando mensaje de progreso semanal")

    # --- Limpieza de claves viejas ---
    try:
        ayer = (ahora - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
        claves_a_borrar = {c for c in tareas_ejecutadas if ayer in c}
        tareas_ejecutadas.difference_update(claves_a_borrar)
    except Exception:
        log.exception("Error limpiando tareas_ejecutadas")


@tarea_diaria.error
async def tarea_diaria_error(error: Exception):
    # Esto es lo más importante del archivo: sin esto, cualquier excepción
    # no capturada arriba mata el loop para siempre y en silencio.
    log.exception("Excepción no manejada en tarea_diaria, reiniciando el loop", exc_info=error)
    if not tarea_diaria.is_running():
        tarea_diaria.restart()
        log.info("tarea_diaria reiniciada tras error")


webserver.keep_alive()
client.run(TOKEN)

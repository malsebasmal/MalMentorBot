import discord
from discord.ext import tasks, commands
from discord import app_commands
import datetime
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_ASISTENCIA_ID = int(os.getenv("CANAL_ASISTENCIA_ID"))
CANAL_RACHAS_ID = int(os.getenv("CANAL_RACHAS_ID"))
CANAL_PROGRESO_ID = int(os.getenv("CANAL_PROGRESO_ID"))
JOAQUIN_ID = int(os.getenv("JOAQUIN_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ZONA_HORARIA = "America/Lima"

intents = discord.Intents.default()

class MiBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Comandos slash sincronizados")

client = MiBot()

@client.event
async def on_ready():
    print(f"✅ Bot conectado como {client.user}")
    tarea_diaria.start()

@client.tree.command(name="ping", description="Verifica que el bot esté activo")
async def ping(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ No tenés permisos.", ephemeral=True)
        return

    zona = pytz.timezone(ZONA_HORARIA)
    ahora = datetime.datetime.now(zona)
    await interaction.response.send_message(
        f"✅ **Bot activo**\n"
        f"🕐 Hora Lima: `{ahora.strftime('%d/%m/%Y %H:%M:%S')}`\n"
        f"🤖 Conectado como: `{client.user}`",
        ephemeral=True
    )

@tasks.loop(minutes=1)
async def tarea_diaria():
    zona = pytz.timezone(ZONA_HORARIA)
    ahora = datetime.datetime.now(zona)
    es_laboral = ahora.weekday() <= 4  # 0=lunes, 4=viernes
    es_viernes = ahora.weekday() == 4

    hora = ahora.hour
    minuto = ahora.minute

    # ─────────────────────────────────────────
    # LUNES A VIERNES 8:00 AM — Asistencia con reacción
    # ─────────────────────────────────────────
    if es_laboral and hora == 8 and minuto == 0:
        canal = client.get_channel(CANAL_ASISTENCIA_ID)
        if canal:
            mensaje = await canal.send(
                f"📋 ¡Buenos días <@{JOAQUIN_ID}>!\n"
                "Reaccioná con ✅ para confirmar tu asistencia de hoy."
            )
            await mensaje.add_reaction("✅")

    # ─────────────────────────────────────────
    # LUNES A VIERNES 8:00 PM — Recordatorio racha LionBot
    # ─────────────────────────────────────────
    if es_laboral and hora == 20 and minuto == 0:
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

    # ─────────────────────────────────────────
    # VIERNES 8:00 PM — Resumen semanal en #progreso
    # ─────────────────────────────────────────
    if es_viernes and hora == 20 and minuto == 0:
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

client.run(TOKEN)
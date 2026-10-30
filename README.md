# boca-bot-telegram

Bot que avisa por Telegram **a las 9:00 del día del partido** que juega
Boca Juniors, con un mensaje listo para copiar y pegar en WhatsApp.

```
HOY JUEGA BOOOCAA !!! 💙💛
⚽ Boca Juniors vs River Plate
🏟️ Alberto José Armando (La Bombonera) (Boca de local)
🕒 domingo 01/11 15:00 hs (hora Arg)
🏆 Liga Profesional
```

Los días sin partido manda `Hoy no jugamos compa, el dia es una mierda :(`.
Esa señal es a propósito: **si un día a las 9:30 no te llegó nada, algo se
rompió.**

No usa cuentas de fútbol ni claves de API, ni librerías externas: solo
Python estándar y GitHub Actions (gratis, sin servidor propio).

## Cómo funciona

[`scripts/match_day.py`](scripts/match_day.py) lee dos fuentes, decide qué
mandar y guarda en [`data/state.json`](data/state.json) qué mandó, así
puede correr varias veces sin repetir mensajes.

| Fuente | Qué aporta | Riesgo |
|---|---|---|
| API pública de ESPN | Estadio, competición, si el horario está confirmado, si se postergó | No es oficial, puede cambiar sin aviso |
| Calendario público de fixtur.es | Control cruzado y respaldo | Proyecto chico; solo trae estadio en copas internacionales |

Ninguna pide cuenta. El calendario es el mismo que aparece en Google
Calendar, pero se lee con su link público, sin entrar a ninguna cuenta.

### Qué manda en cada caso

| Situación a las 9:00 | Mensaje |
|---|---|
| Hay partido y las fuentes coinciden | El aviso normal |
| Hay partido sin horario confirmado | El aviso con "horario a confirmar" |
| Las fuentes dan distinta hora | El aviso con la hora y ", a confirmar" |
| Una fuente dice hoy y la otra no | "⚠️ Posible partido hoy", con lo que dice cada una |
| Una fuente falla | El aviso con la otra, más un "🔧 Aviso técnico" aparte |
| ESPN lo marca postergado o cancelado | "⚠️ El partido de hoy figura postergado o cancelado" |
| No hay partido | "Hoy no jugamos..." |
| Las dos fuentes fallan | "Perdon, flashe fruta" y qué falló; se reintenta |

Si alguna fuente o Telegram fallan, la corrida queda en **rojo** en GitHub.

### Disparos

Corre tres veces por día y manda un solo mensaje:

1. **9:00 y 9:30 hora Argentina, desde cron-job.org.** Es el disparo
   principal porque es puntual (medido: 31 a 70 segundos después de la
   hora). Llama a la API de GitHub.
2. **`schedule` de GitHub, de respaldo.** Se atrasa horas (medido: entre 4
   y 9hs), así que no alcanza para las 9:00. Si llega antes de las 9:05
   espera hasta esa hora; si cron-job.org dejó de andar, el aviso sale
   igual, más tarde.

Config de los dos jobs de cron-job.org (zona horaria
`America/Argentina/Buenos_Aires`):

| Campo | Valor |
|---|---|
| URL | `https://api.github.com/repos/chiffoneg/boca-bot-telegram/actions/workflows/match-day.yml/dispatches` |
| Método | `POST` |
| Body | `{"ref":"main"}` |
| Header `Authorization` | `Bearer <PAT fine-grained>` |
| Header `Accept` | `application/vnd.github+json` |
| Header `X-GitHub-Api-Version` | `2026-03-10` |
| Header `Content-Type` | `application/json` |

El PAT es *fine-grained*, con acceso **solo a este repo** y permiso
**Actions: Read and write**. ⏳ Vence el **8/9/2027**: al regenerarlo,
elegí sin vencimiento si GitHub lo ofrece. Si vence, el bot sigue por el
respaldo de GitHub, pero más tarde. GitHub avisa con años de anticipación
cuando una versión de su API va a dejar de andar: si el disparo empieza a
fallar, revisá también ese header.

## Setup

En GitHub: **Settings → Secrets and variables → Actions**.

| Secret | De dónde sale |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Te lo da @BotFather al crear el bot |
| `TELEGRAM_CHAT_ID` | Tu chat_id, vía `getUpdates` de la API de Telegram |

## Probar

Desde la pestaña Actions:

- **Aviso del dia (Boca)** → Run workflow, con `dry_run` tildado: muestra en
  el log qué mandaría, sin mandar nada. Con `date` simula otro día.
- **Test Telegram message**: manda un mensaje de prueba con el formato real.

Local:

```bash
python -m unittest discover -s tests
python scripts/match_day.py --dry-run --date 2026-11-01
```

Los tests usan respuestas reales guardadas en
[`tests/fixtures`](tests/fixtures) y corren con cada cambio de código. A
propósito no corren antes del aviso: un test roto no debe frenar el mensaje.

## Si algo se rompe

| Síntoma | Qué mirar |
|---|---|
| "🔧 Aviso técnico" o error de ESPN/calendario | El formato de la fuente cambió: [`espn.py`](scripts/lib/espn.py) o [`calendar_feed.py`](scripts/lib/calendar_feed.py) |
| El aviso llega tarde (cerca del mediodía) | cron-job.org o su token: revisar el job y si venció el PAT |
| No llega nada | Pestaña Actions: que el workflow siga habilitado |

**GitHub apaga los `schedule` si el repo está 60 días sin actividad.** El
commit diario de `data/state.json` debería evitarlo. Si pasara, se
reactiva con un click en la pestaña Actions.

Si un partido arranca antes de las 9:00, el aviso sale tarde: no pasó
nunca en 2026 (el más temprano fue a las 14:00).

## Pendientes

- **Multi-destinatario**: hoy `TELEGRAM_CHAT_ID` es un solo valor, pero
  [`telegram.py`](scripts/lib/telegram.py) está aislado, así que es un
  cambio chico.

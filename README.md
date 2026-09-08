# boca-bot-telegram

Bot que avisa por Telegram **5 horas antes** de cada partido de Boca
Juniors, con un mensaje ya armado y listo para copiar y pegar en
WhatsApp.

Además, todos los días manda una señal corta de vida: si hay partido,
confirma que lo agendó y a qué hora te va a avisar; si no hay, te lo
dice igual. Así, si un día no te llega nada, ya sabés que algo se rompió.

## Cómo funciona

Dos procesos separados, corridos por GitHub Actions (gratis, sin
servidor propio):

1. **`daily-check.yml`** — corre 1 vez por día, a las 3am hora
   Argentina. Llama a la API de fútbol (API-Football), busca si Boca
   tiene partido en las próximas ~22 horas y:
   - **Si hay**: arma el mensaje completo, calcula la hora exacta de
     envío (hora del partido − 5 horas), lo guarda en
     [`data/next_match.json`](data/next_match.json) y te manda una
     **confirmación de agendado** ("✅ Hay partido de Boca... te aviso a
     las 16:30 hs"). El aviso completo todavía no sale acá.
   - **Si no hay**: te manda `"Hoy no jugamos compa, el dia es una
     mierda :("`.
   - **Si falla**: te manda `"Perdon, flashe fruta 😶‍🌫️"`. El detalle
     técnico del error queda en los logs del workflow, no en el chat.

2. **`watcher.yml`** — corre cada pocos minutos. **No** llama a ninguna
   API de fútbol: solo lee `data/next_match.json` y compara la hora
   actual contra la hora de envío guardada. Si ya se cumplió, manda el
   mensaje por Telegram y marca el archivo como enviado (para no
   duplicar).
   **Fallback**: si esa hora ya pasó para cuando el watcher la nota (por
   ejemplo un partido muy temprano a la mañana), lo manda igual en el
   primer run que lo detecta, en vez de perderlo.

Presupuesto de la API: 1-3 pedidos por día, muy lejos del límite de
100/día del plan free.

## ⚠️ Importante: el cron nativo de GitHub no alcanza

El trigger `schedule:` de GitHub Actions tiene **prioridad baja** y en
repos poco activos se atrasa **horas** (lo medimos: corridas cada 3-5hs
en vez de cada 10 min). Eso hacía que el aviso de "5 horas antes"
llegara tarde o directamente no llegara.

Por eso el watcher se dispara **desde afuera**: un cronjob gratuito en
[cron-job.org](https://cron-job.org) llama cada pocos minutos a la API
de GitHub para disparar el workflow, y esos triggers sí se ejecutan al
instante. El `schedule:` del workflow quedó igual, solo como backup.

Config del cronjob externo:

| Campo | Valor |
|---|---|
| URL | `https://api.github.com/repos/chiffoneg/boca-bot-telegram/actions/workflows/watcher.yml/dispatches` |
| Método | `POST` |
| Body | `{"ref":"main"}` |
| Header `Authorization` | `Bearer <PAT fine-grained>` |
| Header `Accept` | `application/vnd.github+json` |
| Header `X-GitHub-Api-Version` | `2022-11-28` |
| Header `Content-Type` | `application/json` |

El PAT es *fine-grained*, con acceso **solo a este repo** y permiso
**Actions: Read and write**. ⏳ **Vence en 1 año** — cuando pase, hay que
regenerarlo y actualizarlo en cron-job.org, o el bot deja de avisar.

## Setup

### 1. Secrets del repo

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**.
Cargá estos tres (los valores nunca se escriben en el código ni quedan
en el historial de git):

| Secret | De dónde sale |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Te lo da @BotFather al crear el bot |
| `TELEGRAM_CHAT_ID` | Tu chat_id, vía `getUpdates` de la API de Telegram |
| `API_FOOTBALL_KEY` | Dashboard de api-football.com |

### 2. (Opcional) Variable BOCA_TEAM_ID

El código asume que el ID de Boca Juniors en API-Football es `451`.
Confirmalo así:

```bash
set API_FOOTBALL_KEY=tu_key
python scripts/find_team_id.py
```

Si te da un ID distinto a 451, cargalo en **Settings → Secrets and
variables → Actions → Variables → New repository variable**, nombre
`BOCA_TEAM_ID`. No hace falta que sea un secret porque no es información
sensible.

### 3. Probar sin esperar al cron

Todos los workflows tienen `workflow_dispatch` (botón "Run workflow" en
la pestaña Actions):

- **Test Telegram message** — manda un mensaje de prueba con el formato
  real, sin gastar pedidos de la API de fútbol.
- **Daily check (Boca fixtures)** — corre el chequeo real contra la API.
  Gasta 1-3 pedidos de los 100 diarios.
- **Watcher (mandar aviso de partido)** — actúa según lo que encuentre
  en `data/next_match.json` en ese momento.

## Formato de `data/next_match.json`

```jsonc
{
  "status": "scheduled",   // empty | no_match | scheduled | sent
  "checked_at_utc": "...",
  "fixture_id": 1629830,
  "match_utc": "...",
  "send_at_utc": "...",    // hora del aviso (partido - 5h)
  "message": "...",        // aviso ya armado, listo para mandar
  "sent": false,
  "sent_at_utc": null
}
```

## Limitaciones a tener en cuenta

- **El chequeo diario corre 1 sola vez.** Si justo en ese momento la API
  está caída, te llega el mensaje de error pero **nadie reintenta** ese
  día. Correrlo 2-3 veces por día lo resolvería (hay presupuesto de
  sobra en la API).
- **GitHub apaga solo los cron si el repo está 60 días sin actividad.**
  El bot commitea seguido, así que no debería pasar, pero si un día deja
  de andar, revisá que los workflows sigan habilitados.
- El plan free de API-Football tiene restricciones no documentadas
  claramente que fuimos encontrando en la práctica: el parámetro `next`
  de `/fixtures` y el parámetro `last` de `/fixtures/headtohead` están
  bloqueados, y filtrar `/fixtures` por `team`+`season` solo funciona
  para temporadas viejas (2022-2024), no la actual. El código ya
  esquiva estas tres cosas (ver comentarios en
  [`scripts/lib/api_football.py`](scripts/lib/api_football.py)), pero
  si la API cambia de comportamiento de nuevo, revisar ahí primero.

## Roadmap / pendientes

- **Historial de enfrentamientos (H2H)**: implementado pero
  **desactivado**. `build_h2h_section()` incluía partidos futuros o no
  jugados (incluido el propio partido que se estaba avisando) como si
  fueran "últimos enfrentamientos". Falta filtrar por partidos ya
  finalizados antes de volver a engancharlo en `daily_check.py`.
- **Sin tests automatizados**: todo el testing fue manual vía workflows.
  Un par de tests de `build_message` y del cálculo de horarios evitarían
  regresiones como la del H2H.
- **Multi-destinatario**: hoy `TELEGRAM_CHAT_ID` es un solo valor, pero
  `lib/telegram.py` está aislado, así que agregar una lista de chat_ids
  es un cambio chico y localizado, no un rediseño.

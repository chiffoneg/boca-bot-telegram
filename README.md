# boca-bot-telegram

Bot que avisa por Telegram, 5 horas antes de cada partido de Boca
Juniors, un mensaje ya armado y listo para copiar y pegar en WhatsApp.

## Cómo funciona

Dos procesos separados, corridos por GitHub Actions (gratis, sin
servidor propio):

1. **`daily-check.yml`** — corre 1 sola vez por día, a las 3am hora
   Argentina. Llama UNA vez a la API de fútbol (API-Football), busca si
   Boca tiene partido en las próximas ~22 horas y, si lo hay, arma el
   mensaje y calcula la hora exacta de envío (hora del partido − 5
   horas). Guarda todo en [`data/next_match.json`](data/next_match.json)
   y lo commitea al repo. Acá todavía **no se manda nada**.
2. **`watcher.yml`** — corre cada 15 minutos. **No** llama a ninguna
   API de fútbol: solo lee `data/next_match.json` y compara la hora
   actual contra la hora de envío guardada. Si ya se cumplió, manda el
   mensaje por Telegram y marca el archivo como enviado (para no
   duplicar).
3. **Fallback**: si por algún motivo la hora ideal de envío ya pasó
   cuando el watcher la nota (por ejemplo un partido muy temprano a la
   mañana), lo manda igual en el primer run que lo detecta, en vez de
   perderlo.

Con esto se gasta como mucho **1 pedido a la API por día** (el plan
gratuito de API-Football da 100/día), y el watcher no toca la API para
nada.

## Setup

### 1. Secrets del repo

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**.
Cargá estos tres (los valores nunca se escriben en el código ni quedan
en el historial de git):

| Secret | De dónde sale |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Te lo da @BotFather al crear el bot |
| `TELEGRAM_CHAT_ID` | Tu chat_id, ver `getUpdates` en la guía que te pasé por chat |
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

### 3. Probar antes de confiar en el cron

Todo tiene "botón de prueba manual" (`workflow_dispatch`), así que no
hace falta esperar al horario del cron para ver si funciona:

- **Probar Telegram de punta a punta** (sin gastar pedidos de la API de
  fútbol): pestaña **Actions** no hace falta, se corre local:
  ```bash
  set TELEGRAM_BOT_TOKEN=...
  set TELEGRAM_CHAT_ID=...
  python scripts/send_test_message.py
  ```
  Manda un mensaje de prueba con el formato real (aclarado como prueba)
  a tu Telegram.
- **Probar el chequeo diario contra la API real**: pestaña **Actions**
  → *Daily check (Boca fixtures)* → **Run workflow**. Gasta 1 pedido de
  los 100 diarios. Revisá el log y el contenido de
  `data/next_match.json` después de correrlo.
- **Probar el watcher**: pestaña **Actions** → *Watcher (mandar aviso
  de partido)* → **Run workflow**. Si `data/next_match.json` tiene un
  partido programado y ya pasó la hora de envío, te llega el mensaje.

Recién después de ver estas tres pruebas OK conviene dejarlo corriendo
solo con el cron.

## Limitaciones a tener en cuenta

- **Los cron de GitHub Actions no son puntuales al segundo**: pueden
  atrasarse varios minutos en horas pico. Por eso el watcher corre cada
  15 minutos y no una vez justo a la hora calculada.
- **GitHub apaga solo los cron si el repo está 60 días sin actividad**
  (sin commits). Si pasa mucho tiempo sin que juegue Boca... en
  realidad juega bastante seguido, así que no debería ser un problema
  real, pero si alguna vez el bot deja de mandar avisos, revisá que los
  workflows sigan habilitados en la pestaña Actions.
- Si `daily-check.yml` falla (API caída, key vencida, etc.), te llega
  un mensaje de error por Telegram avisando que hay que revisar a mano
  ese día.

## Roadmap

- El historial de enfrentamientos entre los equipos (head-to-head) no
  está en esta primera versión — queda para una siguiente iteración.
- Pensado para escalar a más de un destinatario más adelante: hoy
  `TELEGRAM_CHAT_ID` es un solo valor, pero `lib/telegram.py` está
  aislado así que agregar una lista de chat_ids es un cambio chico y
  localizado, no un rediseño.

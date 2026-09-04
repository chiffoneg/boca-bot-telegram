# boca-bot-telegram

Bot que avisa por Telegram antes de cada partido de Boca Juniors:

1. **5 horas antes**: mensaje con quién juega, dónde, cuándo, en qué
   torneo y el historial de los últimos enfrentamientos — listo para
   copiar y pegar en WhatsApp.
2. **30/20/10 minutos antes**: en cuanto la API publica las
   alineaciones, dos mensajes más (texto + imagen) con el 11 titular de
   ambos equipos.

## Cómo funciona

Dos procesos separados, corridos por GitHub Actions (gratis, sin
servidor propio):

1. **`daily-check.yml`** — corre 1 sola vez por día, a las 3am hora
   Argentina. Llama a la API de fútbol (API-Football), busca si Boca
   tiene partido en las próximas ~22 horas y, si lo hay:
   - arma el mensaje principal y calcula la hora exacta de envío (hora
     del partido − 5 horas);
   - le agrega la sección de historial de enfrentamientos (H2H) contra
     el rival, si la API tiene datos;
   - inicializa el seguimiento de alineaciones (`lineups_status:
     pending`).

   Guarda todo en [`data/next_match.json`](data/next_match.json) y lo
   commitea al repo. Acá todavía **no se manda nada**.

2. **`watcher.yml`** — corre cada 10 minutos y maneja dos avisos
   independientes:
   - **Aviso principal**: no llama a la API, solo compara la hora
     actual contra la hora de envío guardada y manda el mensaje ya
     armado cuando corresponde.
     **Fallback**: si esa hora ya pasó para cuando el watcher la nota
     (por ejemplo un partido muy temprano a la mañana), lo manda igual
     en el primer run que lo detecta, en vez de perderlo.
   - **Alineaciones**: acá sí llama a la API, pero solo en las ventanas
     de 30, 20 y 10 minutos antes del partido — cada una se intenta una
     única vez, se haya encontrado la data o no. En cuanto aparecen,
     manda dos mensajes separados (texto y después la imagen) y deja de
     intentar. Si llega la hora del partido sin haberlas encontrado, no
     manda nada más (no siempre se publican a tiempo, sobre todo en
     torneos/categorías con menos cobertura de datos).

Presupuesto de la API: como mucho ~4-5 pedidos por día (1-3 del chequeo
diario + 1 de historial + hasta 3 de alineaciones, solo en días de
partido), muy lejos del límite de 100/día del plan free.

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
  fútbol): pestaña **Actions** → *Test Telegram message* → **Run
  workflow**. Manda un mensaje de prueba con el formato real (aclarado
  como prueba) usando los Secrets ya cargados en GitHub.
- **Probar las alineaciones** (texto + imagen) sin esperar a un
  partido real: pestaña **Actions** → *Test lineups message* → **Run
  workflow**. Usa datos ficticios.
- **Probar el chequeo diario contra la API real**: pestaña **Actions**
  → *Daily check (Boca fixtures)* → **Run workflow**. Gasta 1-2 pedidos
  de los 100 diarios. Revisá el log y el contenido de
  `data/next_match.json` después de correrlo.
- **Probar el watcher**: pestaña **Actions** → *Watcher (mandar aviso
  de partido y alineaciones)* → **Run workflow**. Actúa según lo que
  encuentre en `data/next_match.json` en ese momento.

Recién después de ver estas pruebas OK conviene dejarlo corriendo solo
con el cron.

## Formato de `data/next_match.json`

```jsonc
{
  "status": "scheduled",       // empty | no_match | scheduled | sent
  "fixture_id": 1493113,
  "match_utc": "...",
  "send_at_utc": "...",        // hora del aviso principal (partido - 5h)
  "message": "...",            // aviso principal ya armado, con H2H incluido
  "sent": false,
  "lineups_status": "pending", // not_applicable | pending | sent | given_up
  "lineups_checked_tiers": []  // qué ventanas (30/20/10 min) ya se intentaron
}
```

## Limitaciones a tener en cuenta

- **Los cron de GitHub Actions no son puntuales al segundo**: pueden
  atrasarse varios minutos en horas pico. El watcher corre cada 10
  minutos, así que los umbrales de 30/20/10 min de alineaciones son
  aproximados, no exactos al minuto.
- **Las alineaciones no siempre se publican a tiempo** (o no se
  publican) en la API, sobre todo en torneos/categorías con menos
  cobertura de datos (Copa Argentina en instancias tempranas, por
  ejemplo). Si no llegan, el bot no manda nada — no hay aviso de "no
  hay alineaciones" para no generar ruido.
- **GitHub apaga solo los cron si el repo está 60 días sin actividad**
  (sin commits). Si alguna vez el bot deja de mandar avisos, revisá que
  los workflows sigan habilitados en la pestaña Actions.
- Si `daily-check.yml` falla (API caída, key vencida, etc.), te llega
  un mensaje corto de error por Telegram ("Perdon, flashe fruta 😶‍🌫️");
  el detalle técnico completo queda en los logs del workflow.
- El plan free de API-Football tiene restricciones no documentadas
  claramente que fuimos encontrando en la práctica: el parámetro `next`
  de `/fixtures` y el parámetro `last` de `/fixtures/headtohead` están
  bloqueados, y filtrar `/fixtures` por `team`+`season` solo funciona
  para temporadas viejas (2022-2024), no la actual. El código ya
  esquiva estas tres cosas (ver comentarios en
  [`scripts/lib/api_football.py`](scripts/lib/api_football.py)), pero
  si la API cambia de comportamiento de nuevo, revisar ahí primero.

## Roadmap

- Pensado para escalar a más de un destinatario más adelante: hoy
  `TELEGRAM_CHAT_ID` es un solo valor, pero `lib/telegram.py` está
  aislado así que agregar una lista de chat_ids es un cambio chico y
  localizado, no un rediseño.

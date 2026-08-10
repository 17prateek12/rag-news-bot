const VOICE_LIMIT = 5
const PREFIX = 'context_voice_quota_'

function todayKey() {
  return new Date().toISOString().slice(0, 10)
}

interface QuotaRecord {
  date: string
  count: number
}

function read(userId: string): QuotaRecord {
  try {
    const raw = localStorage.getItem(`${PREFIX}${userId}`)
    if (!raw) return { date: todayKey(), count: 0 }
    const parsed = JSON.parse(raw) as QuotaRecord
    if (parsed.date !== todayKey()) return { date: todayKey(), count: 0 }
    return parsed
  } catch {
    return { date: todayKey(), count: 0 }
  }
}

function write(userId: string, record: QuotaRecord) {
  localStorage.setItem(`${PREFIX}${userId}`, JSON.stringify(record))
}

export function getVoiceRemaining(userId: string) {
  const record = read(userId)
  return Math.max(0, VOICE_LIMIT - record.count)
}

export function canUseVoice(userId: string) {
  return getVoiceRemaining(userId) > 0
}

export function consumeVoice(userId: string) {
  const record = read(userId)
  if (record.count >= VOICE_LIMIT) return false
  write(userId, { ...record, count: record.count + 1 })
  return true
}

export const VOICE_MESSAGE_LIMIT = VOICE_LIMIT

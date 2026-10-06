// Lets any page open the chat panel, optionally sending a question straight away
// ("Ask about this item", playbook chips, sold-out rescue, pennants...).
const OPEN_CHAT = 'cc:open-chat'

export const openChat = (prompt?: string) =>
  window.dispatchEvent(new CustomEvent(OPEN_CHAT, { detail: { prompt } }))

export function onOpenChat(handler: (prompt?: string) => void) {
  const listener = (e: Event) => handler((e as CustomEvent<{ prompt?: string }>).detail?.prompt)
  window.addEventListener(OPEN_CHAT, listener)
  return () => window.removeEventListener(OPEN_CHAT, listener)
}

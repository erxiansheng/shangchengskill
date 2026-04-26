import { get, post, put, del } from './request.js'

export function getFavorites(params = {}) {
    return get('/favorites', params)
}

export function addFavorite(skillId) {
    return post('/favorites', { skill_id: skillId })
}

export function removeFavorite(skillId) {
    return del(`/favorites/${skillId}`)
}

export function getMessages(params = {}) {
    return get('/messages', params)
}

export function markRead(messageId) {
    return put(`/messages/${messageId}/read`)
}

export function markAllRead() {
    return put('/messages/read-all')
}

export function getUnreadCount() {
    return get('/messages/unread-count')
}

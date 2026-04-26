import { get, post, put, del } from './request.js'

export function getTokens() {
    return get('/tokens')
}

export function createToken(data) {
    return post('/tokens', data)
}

export function updateToken(tokenId, data) {
    return put(`/tokens/${tokenId}`, data)
}

export function toggleToken(tokenId) {
    return fetch(`/api/v1/tokens/${tokenId}/toggle`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('EdgeOneMall_token')}`,
        },
    }).then(r => r.json())
}

export function revokeToken(tokenId) {
    return del(`/tokens/${tokenId}`)
}

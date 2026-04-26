import { post } from './request.js'

export function login(username, password) {
    return post('/auth/login', { username, password })
}

export function register(data) {
    return post('/auth/register', data)
}

export function refreshToken(refresh_token) {
    return post('/auth/refresh', { refresh_token })
}

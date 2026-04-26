import { get, post, put, del } from './request.js'

export function getMe() {
    return get('/users/me')
}

export function updateProfile(data) {
    return put('/users/me', data)
}

export function getUserProfile(userId) {
    return get(`/users/${userId}/profile`)
}

export function followUser(userId) {
    return post(`/users/${userId}/follow`)
}

export function unfollowUser(userId) {
    return del(`/users/${userId}/follow`)
}

export function checkFollow(userId) {
    return get(`/users/${userId}/follow/check`)
}

import { get, post, put, del } from './request.js'

export function getSkills(params = {}) {
    return get('/skills', params)
}

export function getSkillDetail(id) {
    return get(`/skills/${id}`)
}

export function createSkill(data) {
    return post('/skills', data)
}

export function updateSkill(id, data) {
    return put(`/skills/${id}`, data)
}

export function getMySkills(params = {}) {
    return get('/skills/my', params)
}

export function getSkillVersions(id) {
    return get(`/skills/${id}/versions`)
}

export function createVersion(skillId, data) {
    return post(`/skills/${skillId}/versions`, data)
}

export function getCategories() {
    return get('/categories')
}

export function getSkillReviews(skillId, params = {}) {
    return get(`/skills/${skillId}/reviews`, params)
}

export function createReview(skillId, data) {
    return post(`/skills/${skillId}/reviews`, data)
}

export function deleteReview(reviewId) {
    return del(`/reviews/${reviewId}`)
}

export function getCaptcha() {
    return get('/captcha')
}

export function deleteSkill(id) {
    return del(`/skills/${id}`)
}

export function offlineSkill(id) {
    return post(`/skills/${id}/offline`)
}

export function onlineSkill(id) {
    return post(`/skills/${id}/online`)
}

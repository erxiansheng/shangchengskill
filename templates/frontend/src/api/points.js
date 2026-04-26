import { get, post } from './request.js'

export function getBalance() {
    return get('/points/balance')
}

export function getRecords(params = {}) {
    return get('/points/records', params)
}

export function getPackages() {
    return get('/points/packages')
}

export function createRecharge(data) {
    return post('/points/recharge', data)
}

export function checkRechargeStatus(orderNo) {
    return get(`/points/recharge/${orderNo}/status`)
}

export function requestWithdrawal(data) {
    return post('/points/withdraw', data)
}

export function getWithdrawals(params = {}) {
    return get('/points/withdrawals', params)
}

export function purchaseSkill(skill_id) {
    return post('/purchases', { skill_id })
}

export function getPurchases(params = {}) {
    return get('/purchases', params)
}

export function checkPurchase(skillId) {
    return get(`/purchases/${skillId}/check`)
}

export function downloadSkill(skillId) {
    return get(`/purchases/${skillId}/download`)
}

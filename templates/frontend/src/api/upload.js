import { post } from './request.js'

export function uploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    return post('/upload/image', formData)
}

export function uploadSkillPackage(file) {
    const formData = new FormData()
    formData.append('file', file)
    return post('/upload/skill-package', formData)
}

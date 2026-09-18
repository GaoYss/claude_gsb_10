import { createResourceApi } from './client'
import http from './client'

export const greenWasteApi = {
  ...createResourceApi('green-wastes'),
  summary: (params) => http.get('/green-wastes/summary', { params }),
}

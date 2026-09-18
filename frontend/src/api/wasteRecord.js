import { createResourceApi } from './client'
import http from './client'

export const wasteRecordApi = {
  ...createResourceApi('waste-records'),
  summary: (params) => http.get('/waste-records/summary', { params }),
  monthly: (params) => http.get('/waste-records/monthly', { params }),
}

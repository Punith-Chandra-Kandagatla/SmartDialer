import axios from 'axios'

const api = axios.create({
  baseURL: '/',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const getDashboardOverview = async () => {
  const response = await api.get('/api/v1/dashboard/overview')
  return response.data
}

export const getCampaigns = async () => {
  const response = await api.get('/api/v1/campaigns/')
  return response.data
}

export const createCampaign = async (campaignData) => {
  const response = await api.post('/api/v1/campaigns/', campaignData)
  return response.data
}

export const updateCampaignStatus = async (campaignId, status) => {
  const response = await api.patch(
    `/api/v1/campaigns/${campaignId}/status`,
    null,
    {
      params: { status },
    }
  )

  return response.data
}

export default api
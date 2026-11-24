import { useEffect, useState } from 'react'

import {
  getDashboardOverview,
  getCampaigns,
  createCampaign,
  updateCampaignStatus,
} from '../services/api'

import {
  Activity,
  Users,
  Phone,
  Target,
  RefreshCw,
  AlertCircle,
  Plus,
  X,
  CheckCircle2,
} from 'lucide-react'

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'

const initialMetrics = {
  campaigns: { total: 0, by_status: {} },
  agents: { total: 0, by_status: {} },
  borrowers: { total: 0, by_status: {} },
  calls: { total: 0, by_status: {} },
}

const initialFormData = {
  name: '',
  description: '',
  dialing_mode: 'PROGRESSIVE',
  max_concurrent_calls: 50,
  max_attempts_per_borrower: 3,
  target_answer_rate: 0.4,
  max_abandoned_rate: 0.03,
}

function Dashboard() {
  const [metrics, setMetrics] = useState(initialMetrics)
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [updatingCampaign, setUpdatingCampaign] = useState(null)

  const [formError, setFormError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [formData, setFormData] = useState(initialFormData)

  // LOAD DASHBOARD DATA

  const loadDashboard = async () => {
    try {
      setError('')

      const [overview, campaignData] = await Promise.all([
        getDashboardOverview(),
        getCampaigns(),
      ])

      setMetrics(overview)
      setCampaigns(campaignData)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Unable to connect to SmartDialer backend.'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()

    const interval = setInterval(loadDashboard, 10000)

    return () => clearInterval(interval)
  }, [])

  // FORM HANDLING

  const handleFormChange = (event) => {
    const { name, value } = event.target

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  // CREATE CAMPAIGN

  const handleCreateCampaign = async (event) => {
    event.preventDefault()

    setCreating(true)
    setFormError('')
    setSuccessMessage('')

    try {
      const payload = {
        ...formData,
        max_concurrent_calls: Number(formData.max_concurrent_calls),
        max_attempts_per_borrower: Number(
          formData.max_attempts_per_borrower
        ),
        target_answer_rate: Number(formData.target_answer_rate),
        max_abandoned_rate: Number(formData.max_abandoned_rate),
      }

      await createCampaign(payload)

      setFormData(initialFormData)
      setShowCreateModal(false)
      setSuccessMessage('Campaign created successfully.')

      await loadDashboard()

      setTimeout(() => {
        setSuccessMessage('')
      }, 5000)

    } catch (err) {
      const detail = err.response?.data?.detail

      setFormError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(', ')
          : detail || 'Campaign creation failed.'
      )
    } finally {
      setCreating(false)
    }
  }

  // CAMPAIGN STATUS MANAGEMENT

  const handleCampaignStatus = async (campaignId, status) => {
    try {
      setUpdatingCampaign(campaignId)
      setError('')
      setSuccessMessage('')

      await updateCampaignStatus(campaignId, status)

      await loadDashboard()

      const messages = {
        RUNNING: 'Campaign started successfully.',
        PAUSED: 'Campaign paused successfully.',
        COMPLETED: 'Campaign completed successfully.',
      }

      setSuccessMessage(
        messages[status] || 'Campaign status updated successfully.'
      )

      setTimeout(() => {
        setSuccessMessage('')
      }, 5000)

    } catch (err) {
      const detail = err.response?.data?.detail

      setError(
        typeof detail === 'string'
          ? detail
          : 'Unable to update campaign status.'
      )
    } finally {
      setUpdatingCampaign(null)
    }
  }

  // MODAL CONTROLS

  const openCreateModal = () => {
    setFormError('')
    setShowCreateModal(true)
  }

  const closeCreateModal = () => {
    if (creating) return

    setShowCreateModal(false)
    setFormError('')
    setFormData(initialFormData)
  }

  // DASHBOARD METRICS

  const cards = [
    {
      title: 'Total Campaigns',
      value: metrics.campaigns.total,
      subtitle: 'Campaigns configured',
      icon: Target,
    },
    {
      title: 'Total Agents',
      value: metrics.agents.total,
      subtitle: 'Registered agents',
      icon: Users,
    },
    {
      title: 'Total Calls',
      value: metrics.calls.total,
      subtitle: 'Calls recorded',
      icon: Phone,
    },
    {
      title: 'Borrowers',
      value: metrics.borrowers.total,
      subtitle: 'Registered borrowers',
      icon: Activity,
    },
  ]

  const callStatuses = metrics.calls.by_status || {}

  const callData = Object.entries(callStatuses).map(
    ([status, count]) => ({
      status: status.replaceAll('_', ' '),
      calls: count,
    })
  )

  if (loading) {
    return (
      <div className="loading-screen">
        Loading SmartDialer...
      </div>
    )
  }

  return (
    <main className="dashboard">

      {/* HEADER */}

      <header className="topbar">
        <div>
          <div className="brand">
            <div className="brand-icon">
              <Activity size={22} />
            </div>

            <span>
              SMART<span className="brand-highlight">DIALER</span>
            </span>
          </div>

          <p className="brand-caption">
            INTELLIGENCE BEHIND EVERY CALL
          </p>
        </div>

        <div className="topbar-right">
          <span className="system-status">
            <span className="status-dot" />
            SYSTEM ONLINE
          </span>

          <button
            className="refresh-button"
            onClick={loadDashboard}
            title="Refresh dashboard"
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      {/* DASHBOARD HEADING */}

      <section className="dashboard-heading">
        <div>
          <p className="eyebrow">
            COMMAND CENTER / OVERVIEW
          </p>

          <h1>Operations Dashboard</h1>

          <p className="heading-description">
            Monitor campaigns, workforce and dialing activity in real time.
          </p>

          <button
            className="create-campaign-button"
            onClick={openCreateModal}
          >
            <Plus size={17} />
            Create Campaign
          </button>
        </div>

        <div className="live-indicator">
          <span className="status-dot" />
          LIVE MONITORING
        </div>
      </section>

      {/* NOTIFICATIONS */}

      {error && (
        <div className="error-banner">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {successMessage && (
        <div className="success-banner">
          <CheckCircle2 size={18} />
          {successMessage}
        </div>
      )}

      {/* METRIC CARDS */}

      <section className="metrics-grid">
        {cards.map((card) => {
          const Icon = card.icon

          return (
            <article className="metric-card" key={card.title}>
              <div className="metric-top">
                <span>{card.title}</span>

                <div className="metric-icon">
                  <Icon size={20} />
                </div>
              </div>

              <h2>{card.value.toLocaleString()}</h2>

              <p>{card.subtitle}</p>
            </article>
          )
        })}
      </section>

      {/* ANALYTICS */}

      <section className="content-grid">

        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h3>Call Activity</h3>
              <p>Recorded calls grouped by current status</p>
            </div>
          </div>

          {callData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={callData}>
                <defs>
                  <linearGradient
                    id="callGradient"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor="#36D6C5"
                      stopOpacity={0.35}
                    />

                    <stop
                      offset="100%"
                      stopColor="#36D6C5"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>

                <CartesianGrid
                  stroke="#263449"
                  strokeDasharray="3 3"
                />

                <XAxis
                  dataKey="status"
                  stroke="#8291A8"
                  tick={{ fontSize: 11 }}
                />

                <YAxis
                  stroke="#8291A8"
                  allowDecimals={false}
                />

                <Tooltip
                  contentStyle={{
                    background: '#111D2D',
                    border: '1px solid #263449',
                    borderRadius: '8px',
                  }}
                />

                <Area
                  type="monotone"
                  dataKey="calls"
                  stroke="#36D6C5"
                  fill="url(#callGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              No call activity recorded yet.
            </div>
          )}
        </article>

        {/* AGENT WORKFORCE */}

        <article className="panel">
          <div className="panel-heading">
            <div>
              <h3>Agent Workforce</h3>
              <p>Current agent distribution</p>
            </div>
          </div>

          <div className="status-list">
            {Object.entries(metrics.agents.by_status).length > 0 ? (
              Object.entries(metrics.agents.by_status).map(
                ([status, count]) => (
                  <div className="status-row" key={status}>
                    <span>
                      {status.replaceAll('_', ' ')}
                    </span>

                    <strong>{count}</strong>
                  </div>
                )
              )
            ) : (
              <div className="empty-state">
                No agents registered yet.
              </div>
            )}
          </div>
        </article>

      </section>

      {/* CAMPAIGN MANAGEMENT */}

      <section className="panel campaigns-panel">
        <div className="panel-heading">
          <div>
            <h3>Campaign Management</h3>
            <p>Recently created campaigns</p>
          </div>

          <span className="campaign-count">
            {campaigns.length} CAMPAIGNS
          </span>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>CAMPAIGN</th>
                <th>MODE</th>
                <th>MAX CALLS</th>
                <th>ANSWER TARGET</th>
                <th>STATUS</th>
                <th>ACTIONS</th>
              </tr>
            </thead>

            <tbody>
              {campaigns.length > 0 ? (
                campaigns.slice(0, 10).map((campaign) => (
                  <tr key={campaign.id}>
                    <td>
                      <strong>{campaign.name}</strong>
                    </td>

                    <td>{campaign.dialing_mode}</td>

                    <td>{campaign.max_concurrent_calls}</td>

                    <td>
                      {(campaign.target_answer_rate * 100).toFixed(0)}%
                    </td>

                    <td>
                      <span
                        className={`campaign-status ${campaign.status.toLowerCase()}`}
                      >
                        {campaign.status}
                      </span>
                    </td>

                    {/* CAMPAIGN ACTIONS */}

                    <td>
                      {updatingCampaign === campaign.id ? (
                        <span className="action-loading">
                          Updating...
                        </span>
                      ) : (
                        <div className="campaign-actions">

                          {campaign.status === 'DRAFT' && (
                            <button
                              className="action-button start"
                              onClick={() =>
                                handleCampaignStatus(
                                  campaign.id,
                                  'RUNNING'
                                )
                              }
                            >
                              Start
                            </button>
                          )}

                          {campaign.status === 'RUNNING' && (
                            <>
                              <button
                                className="action-button pause"
                                onClick={() =>
                                  handleCampaignStatus(
                                    campaign.id,
                                    'PAUSED'
                                  )
                                }
                              >
                                Pause
                              </button>

                              <button
                                className="action-button complete"
                                onClick={() =>
                                  handleCampaignStatus(
                                    campaign.id,
                                    'COMPLETED'
                                  )
                                }
                              >
                                Complete
                              </button>
                            </>
                          )}

                          {campaign.status === 'PAUSED' && (
                            <>
                              <button
                                className="action-button start"
                                onClick={() =>
                                  handleCampaignStatus(
                                    campaign.id,
                                    'RUNNING'
                                  )
                                }
                              >
                                Resume
                              </button>

                              <button
                                className="action-button complete"
                                onClick={() =>
                                  handleCampaignStatus(
                                    campaign.id,
                                    'COMPLETED'
                                  )
                                }
                              >
                                Complete
                              </button>
                            </>
                          )}

                          {campaign.status === 'COMPLETED' && (
                            <span className="action-loading">
                              Finished
                            </span>
                          )}

                        </div>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="empty-state">
                    No campaigns available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* CREATE CAMPAIGN MODAL */}

      {showCreateModal && (
        <div
          className="modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeCreateModal()
            }
          }}
        >
          <div
            className="campaign-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="campaign-modal-title"
          >

            <div className="modal-header">
              <div>
                <p className="eyebrow">
                  CAMPAIGN CONFIGURATION
                </p>

                <h2 id="campaign-modal-title">
                  Create New Campaign
                </h2>

                <p>
                  Configure your outbound dialing strategy.
                </p>
              </div>

              <button
                type="button"
                className="modal-close"
                onClick={closeCreateModal}
                disabled={creating}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateCampaign}>

              <div className="form-group">
                <label htmlFor="campaign-name">
                  Campaign Name
                </label>

                <input
                  id="campaign-name"
                  type="text"
                  name="name"
                  placeholder="e.g. November Recovery Campaign"
                  value={formData.name}
                  onChange={handleFormChange}
                  minLength={3}
                  maxLength={150}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="campaign-description">
                  Description
                </label>

                <textarea
                  id="campaign-description"
                  name="description"
                  placeholder="Describe the purpose of this campaign..."
                  value={formData.description}
                  onChange={handleFormChange}
                  maxLength={2000}
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label htmlFor="dialing-mode">
                  Dialing Strategy
                </label>

                <select
                  id="dialing-mode"
                  name="dialing_mode"
                  value={formData.dialing_mode}
                  onChange={handleFormChange}
                >
                  <option value="PROGRESSIVE">
                    Progressive Dialing
                  </option>

                  <option value="PREDICTIVE">
                    Predictive Dialing
                  </option>
                </select>

                <small>
                  {formData.dialing_mode === 'PROGRESSIVE'
                    ? 'One outbound call is reserved for each available agent.'
                    : 'Adaptive pacing recommends outbound call volume based on agent capacity and answer-rate estimates.'}
                </small>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="max-calls">
                    Maximum Concurrent Calls
                  </label>

                  <input
                    id="max-calls"
                    type="number"
                    name="max_concurrent_calls"
                    min="1"
                    max="10000"
                    value={formData.max_concurrent_calls}
                    onChange={handleFormChange}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="max-attempts">
                    Max Attempts / Borrower
                  </label>

                  <input
                    id="max-attempts"
                    type="number"
                    name="max_attempts_per_borrower"
                    min="1"
                    max="20"
                    value={formData.max_attempts_per_borrower}
                    onChange={handleFormChange}
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="answer-target">
                    Target Answer Rate (%)
                  </label>

                  <input
                    id="answer-target"
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    value={Number(formData.target_answer_rate) * 100}
                    onChange={(event) =>
                      setFormData((previous) => ({
                        ...previous,
                        target_answer_rate:
                          Number(event.target.value) / 100,
                      }))
                    }
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="abandonment-limit">
                    Max Abandonment Rate (%)
                  </label>

                  <input
                    id="abandonment-limit"
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    value={Number(formData.max_abandoned_rate) * 100}
                    onChange={(event) =>
                      setFormData((previous) => ({
                        ...previous,
                        max_abandoned_rate:
                          Number(event.target.value) / 100,
                      }))
                    }
                    required
                  />
                </div>
              </div>

              {formError && (
                <div className="modal-error">
                  <AlertCircle size={17} />
                  {formError}
                </div>
              )}

              <div className="modal-actions">
                <button
                  type="button"
                  className="cancel-button"
                  onClick={closeCreateModal}
                  disabled={creating}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="submit-button"
                  disabled={creating}
                >
                  {creating ? (
                    'Creating...'
                  ) : (
                    <>
                      <Plus size={17} />
                      Create Campaign
                    </>
                  )}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {/* FOOTER */}

      <footer className="dashboard-footer">
        SMARTDIALER <span>•</span> INTELLIGENT DIALING INFRASTRUCTURE
      </footer>

    </main>
  )
}

export default Dashboard
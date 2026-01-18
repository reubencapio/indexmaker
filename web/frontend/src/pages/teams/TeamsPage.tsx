import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Users, 
  Building2, 
  FolderKanban, 
  Plus, 
  Settings, 
  ChevronRight,
  Mail,
  UserPlus,
  Crown,
  Shield,
  Eye,
  Edit3,
  Clock,
  Activity as ActivityIcon
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { toast } from 'sonner'

interface Organization {
  id: string
  name: string
  slug: string
  description: string | null
  logo_url: string | null
  tier: string
  created_at: string
  member_count: number
  project_count: number
  my_role: string
}

interface Member {
  id: string
  user_id: string
  email: string
  full_name: string | null
  role: string
  joined_at: string
}

interface Project {
  id: string
  name: string
  slug: string
  description: string | null
  color: string | null
  icon: string | null
  is_archived: boolean
  created_at: string
  index_count: number
  member_count: number
  my_role: string
}

interface ActivityItem {
  id: string
  activity_type: string
  user_id: string
  user_name: string | null
  target_type: string | null
  target_id: string | null
  target_name: string | null
  created_at: string
}

// API functions
const organizationsApi = {
  list: async (): Promise<Organization[]> => {
    const response = await api.get('/organizations/')
    return response.data
  },
  create: async (data: { name: string; slug: string; description?: string }) => {
    const response = await api.post('/organizations/', data)
    return response.data
  },
  getMembers: async (slug: string): Promise<Member[]> => {
    const response = await api.get(`/organizations/${slug}/members`)
    return response.data
  },
  getProjects: async (slug: string): Promise<Project[]> => {
    const response = await api.get(`/organizations/${slug}/projects`)
    return response.data
  },
  getActivity: async (slug: string): Promise<ActivityItem[]> => {
    const response = await api.get(`/organizations/${slug}/activity`)
    return response.data
  },
  invite: async (slug: string, data: { email: string; role: string }) => {
    const response = await api.post(`/organizations/${slug}/invitations`, data)
    return response.data
  },
  createProject: async (slug: string, data: { name: string; slug: string; description?: string; color?: string; icon?: string }) => {
    const response = await api.post(`/organizations/${slug}/projects`, data)
    return response.data
  },
}

const roleIcons = {
  owner: Crown,
  admin: Shield,
  member: Edit3,
  viewer: Eye,
  editor: Edit3,
  reviewer: Eye,
}

const roleColors = {
  owner: 'text-amber-600 bg-amber-100',
  admin: 'text-purple-600 bg-purple-100',
  member: 'text-blue-600 bg-blue-100',
  viewer: 'text-gray-600 bg-gray-100',
  editor: 'text-green-600 bg-green-100',
  reviewer: 'text-orange-600 bg-orange-100',
}

const activityLabels: Record<string, string> = {
  index_created: 'created an index',
  index_updated: 'updated an index',
  index_deleted: 'deleted an index',
  project_created: 'created a project',
  member_added: 'added a member',
  member_removed: 'removed a member',
  invitation_sent: 'sent an invitation',
  org_created: 'created the organization',
}

export function TeamsPage() {
  const queryClient = useQueryClient()
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null)
  const [activeTab, setActiveTab] = useState<'projects' | 'members' | 'activity'>('projects')
  const [showCreateOrgModal, setShowCreateOrgModal] = useState(false)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [showCreateProjectModal, setShowCreateProjectModal] = useState(false)

  // Form states
  const [newOrgName, setNewOrgName] = useState('')
  const [newOrgSlug, setNewOrgSlug] = useState('')
  const [newOrgDesc, setNewOrgDesc] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectSlug, setNewProjectSlug] = useState('')
  const [newProjectDesc, setNewProjectDesc] = useState('')

  // Queries
  const { data: organizations, isLoading: orgsLoading } = useQuery({
    queryKey: ['organizations'],
    queryFn: organizationsApi.list,
  })

  const { data: members } = useQuery({
    queryKey: ['org-members', selectedOrg?.slug],
    queryFn: () => selectedOrg ? organizationsApi.getMembers(selectedOrg.slug) : Promise.resolve([]),
    enabled: !!selectedOrg,
  })

  const { data: projects } = useQuery({
    queryKey: ['org-projects', selectedOrg?.slug],
    queryFn: () => selectedOrg ? organizationsApi.getProjects(selectedOrg.slug) : Promise.resolve([]),
    enabled: !!selectedOrg,
  })

  const { data: activity } = useQuery({
    queryKey: ['org-activity', selectedOrg?.slug],
    queryFn: () => selectedOrg ? organizationsApi.getActivity(selectedOrg.slug) : Promise.resolve([]),
    enabled: !!selectedOrg,
  })

  // Mutations
  const createOrgMutation = useMutation({
    mutationFn: organizationsApi.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      setSelectedOrg(data)
      setShowCreateOrgModal(false)
      setNewOrgName('')
      setNewOrgSlug('')
      setNewOrgDesc('')
      toast.success('Organization created!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create organization')
    },
  })

  const inviteMutation = useMutation({
    mutationFn: (data: { email: string; role: string }) => 
      organizationsApi.invite(selectedOrg!.slug, data),
    onSuccess: () => {
      setShowInviteModal(false)
      setInviteEmail('')
      setInviteRole('member')
      toast.success('Invitation sent!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to send invitation')
    },
  })

  const createProjectMutation = useMutation({
    mutationFn: (data: { name: string; slug: string; description?: string }) =>
      organizationsApi.createProject(selectedOrg!.slug, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-projects', selectedOrg?.slug] })
      setShowCreateProjectModal(false)
      setNewProjectName('')
      setNewProjectSlug('')
      setNewProjectDesc('')
      toast.success('Project created!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create project')
    },
  })

  // Auto-generate slug from name
  const handleOrgNameChange = (name: string) => {
    setNewOrgName(name)
    setNewOrgSlug(name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''))
  }

  const handleProjectNameChange = (name: string) => {
    setNewProjectName(name)
    setNewProjectSlug(name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''))
  }

  if (orgsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Users className="h-8 w-8 text-primary" />
            Teams
          </h1>
          <p className="text-muted-foreground mt-2">
            Manage your organizations, projects, and team members
          </p>
        </div>
        <Button onClick={() => setShowCreateOrgModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Organization
        </Button>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Organization List (Sidebar) */}
        <div className="col-span-12 lg:col-span-4">
          <div className="bg-card rounded-xl border">
            <div className="p-4 border-b">
              <h2 className="font-semibold flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Your Organizations
              </h2>
            </div>
            <div className="divide-y">
              {organizations && organizations.length > 0 ? (
                organizations.map((org) => (
                  <button
                    key={org.id}
                    onClick={() => setSelectedOrg(org)}
                    className={`w-full p-4 text-left hover:bg-muted/50 transition-colors ${
                      selectedOrg?.id === org.id ? 'bg-primary/5 border-l-2 border-primary' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{org.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {org.member_count} members · {org.project_count} projects
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${roleColors[org.my_role as keyof typeof roleColors] || roleColors.viewer}`}>
                          {org.my_role}
                        </span>
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                  </button>
                ))
              ) : (
                <div className="p-8 text-center text-muted-foreground">
                  <Building2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No organizations yet</p>
                  <p className="text-sm">Create one to start collaborating!</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Organization Details */}
        <div className="col-span-12 lg:col-span-8">
          {selectedOrg ? (
            <div className="space-y-6">
              {/* Org Header */}
              <div className="bg-card rounded-xl border p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-16 w-16 bg-gradient-to-br from-primary to-primary/50 rounded-xl flex items-center justify-center text-2xl font-bold text-white">
                      {selectedOrg.name.charAt(0)}
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold">{selectedOrg.name}</h2>
                      <p className="text-muted-foreground">{selectedOrg.description || `/${selectedOrg.slug}`}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm">
                        <span className="flex items-center gap-1">
                          <Users className="h-4 w-4" />
                          {selectedOrg.member_count} members
                        </span>
                        <span className="flex items-center gap-1">
                          <FolderKanban className="h-4 w-4" />
                          {selectedOrg.project_count} projects
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {['owner', 'admin'].includes(selectedOrg.my_role) && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => setShowInviteModal(true)}>
                          <UserPlus className="h-4 w-4 mr-2" />
                          Invite
                        </Button>
                        <Button variant="ghost" size="icon">
                          <Settings className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="border-b">
                <nav className="flex gap-8">
                  {[
                    { id: 'projects' as const, label: 'Projects', icon: FolderKanban },
                    { id: 'members' as const, label: 'Members', icon: Users },
                    { id: 'activity' as const, label: 'Activity', icon: ActivityIcon },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                        activeTab === tab.id
                          ? 'border-primary text-primary'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <tab.icon className="h-4 w-4" />
                      {tab.label}
                    </button>
                  ))}
                </nav>
              </div>

              {/* Tab Content */}
              {activeTab === 'projects' && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold">Projects</h3>
                    {['owner', 'admin', 'member'].includes(selectedOrg.my_role) && (
                      <Button size="sm" onClick={() => setShowCreateProjectModal(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        New Project
                      </Button>
                    )}
                  </div>
                  
                  {projects && projects.length > 0 ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      {projects.map((project) => (
                        <div
                          key={project.id}
                          className="bg-card rounded-xl border p-4 hover:border-primary transition-colors cursor-pointer"
                        >
                          <div className="flex items-start gap-3">
                            <div 
                              className="h-10 w-10 rounded-lg flex items-center justify-center text-lg"
                              style={{ backgroundColor: project.color || '#e5e7eb' }}
                            >
                              {project.icon || '📁'}
                            </div>
                            <div className="flex-1">
                              <div className="font-medium">{project.name}</div>
                              <p className="text-sm text-muted-foreground line-clamp-2">
                                {project.description || 'No description'}
                              </p>
                              <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                                <span>{project.index_count} indices</span>
                                <span>{project.member_count} members</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-muted/50 rounded-xl p-8 text-center">
                      <FolderKanban className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                      <p className="font-medium">No projects yet</p>
                      <p className="text-sm text-muted-foreground">Create your first project to organize indices</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'members' && (
                <div className="space-y-4">
                  <h3 className="font-semibold">Team Members</h3>
                  <div className="bg-card rounded-xl border divide-y">
                    {members?.map((member) => {
                      const RoleIcon = roleIcons[member.role as keyof typeof roleIcons] || Eye
                      return (
                        <div key={member.id} className="p-4 flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                              <span className="font-medium text-sm">
                                {member.full_name?.[0] || member.email[0].toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <div className="font-medium">{member.full_name || member.email}</div>
                              <div className="text-sm text-muted-foreground">{member.email}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full capitalize ${roleColors[member.role as keyof typeof roleColors] || roleColors.viewer}`}>
                              <RoleIcon className="h-3 w-3" />
                              {member.role}
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {activeTab === 'activity' && (
                <div className="space-y-4">
                  <h3 className="font-semibold">Recent Activity</h3>
                  <div className="space-y-3">
                    {activity && activity.length > 0 ? (
                      activity.map((item) => (
                        <div key={item.id} className="flex items-start gap-3 p-3 bg-card rounded-lg border">
                          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <span className="text-xs font-medium">
                              {item.user_name?.[0] || '?'}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm">
                              <span className="font-medium">{item.user_name}</span>
                              {' '}
                              {activityLabels[item.activity_type] || item.activity_type}
                              {item.target_name && (
                                <>
                                  {' '}
                                  <span className="font-medium">{item.target_name}</span>
                                </>
                              )}
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                              <Clock className="h-3 w-3" />
                              {new Date(item.created_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="bg-muted/50 rounded-xl p-8 text-center">
                        <ActivityIcon className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                        <p className="text-muted-foreground">No activity yet</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-card rounded-xl border p-12 text-center">
              <Users className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
              <h3 className="text-lg font-semibold mb-2">Select an Organization</h3>
              <p className="text-muted-foreground mb-4">
                Choose an organization from the list to view details, or create a new one
              </p>
              <Button onClick={() => setShowCreateOrgModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Organization
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Create Organization Modal */}
      {showCreateOrgModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6">
            <h3 className="text-xl font-bold mb-4">Create Organization</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Organization Name</label>
                <input
                  type="text"
                  value={newOrgName}
                  onChange={(e) => handleOrgNameChange(e.target.value)}
                  placeholder="Acme Capital"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Slug</label>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">/</span>
                  <input
                    type="text"
                    value={newOrgSlug}
                    onChange={(e) => setNewOrgSlug(e.target.value)}
                    placeholder="acme-capital"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description (optional)</label>
                <textarea
                  value={newOrgDesc}
                  onChange={(e) => setNewOrgDesc(e.target.value)}
                  placeholder="What does this organization do?"
                  rows={2}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="ghost" onClick={() => setShowCreateOrgModal(false)}>
                Cancel
              </Button>
              <Button 
                onClick={() => createOrgMutation.mutate({ 
                  name: newOrgName, 
                  slug: newOrgSlug, 
                  description: newOrgDesc || undefined 
                })}
                disabled={!newOrgName || !newOrgSlug || createOrgMutation.isPending}
              >
                {createOrgMutation.isPending ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6">
            <h3 className="text-xl font-bold mb-4">Invite Team Member</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Email Address</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                >
                  <option value="admin">Admin - Can manage members and projects</option>
                  <option value="member">Member - Can create and edit</option>
                  <option value="viewer">Viewer - Read-only access</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="ghost" onClick={() => setShowInviteModal(false)}>
                Cancel
              </Button>
              <Button 
                onClick={() => inviteMutation.mutate({ email: inviteEmail, role: inviteRole })}
                disabled={!inviteEmail || inviteMutation.isPending}
              >
                <Mail className="h-4 w-4 mr-2" />
                {inviteMutation.isPending ? 'Sending...' : 'Send Invite'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6">
            <h3 className="text-xl font-bold mb-4">Create Project</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Project Name</label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => handleProjectNameChange(e.target.value)}
                  placeholder="Q1 2025 Indices"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Slug</label>
                <input
                  type="text"
                  value={newProjectSlug}
                  onChange={(e) => setNewProjectSlug(e.target.value)}
                  placeholder="q1-2025-indices"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description (optional)</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="What indices will this project contain?"
                  rows={2}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="ghost" onClick={() => setShowCreateProjectModal(false)}>
                Cancel
              </Button>
              <Button 
                onClick={() => createProjectMutation.mutate({ 
                  name: newProjectName, 
                  slug: newProjectSlug, 
                  description: newProjectDesc || undefined 
                })}
                disabled={!newProjectName || !newProjectSlug || createProjectMutation.isPending}
              >
                {createProjectMutation.isPending ? 'Creating...' : 'Create Project'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}




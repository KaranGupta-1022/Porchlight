import { useEffect, useMemo } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Polygon, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { LatLngExpression } from 'leaflet'
import type { Gap, Invite, MapData, PublicMember, Reach } from './api'
import { theme } from './theme'

type Props = {
  data: MapData
  reach?: Reach
  gaps: Gap[]
  focus?: [number, number]
  newConnectionId?: string
  onMember: (member: PublicMember) => void
  onInvite: (invite: Invite) => void
  onGap: (gap: Gap) => void
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]!)
}

function icon(content: string, className: string, size = 42): L.DivIcon {
  return L.divIcon({ className: `map-icon ${className}`, html: `<span>${escapeHtml(content)}</span>`, iconSize: [size, size], iconAnchor: [size / 2, size / 2] })
}

function mix(a: number, b: number, ratio: number): number {
  return Math.round(a + (b - a) * Math.max(0, Math.min(1, ratio)))
}

function clusterColor(ratio: number): string {
  return `rgb(${mix(74, 245, ratio)}, ${mix(85, 166, ratio)}, ${mix(104, 35, ratio)})`
}

function FlyTo({ data, focus }: { data: MapData; focus?: [number, number] }) {
  const map = useMap()
  useEffect(() => {
    map.flyTo([data.community.center_lat, data.community.center_lng], data.community.zoom, { duration: 0.7 })
  }, [data.community.id, data.community.center_lat, data.community.center_lng, data.community.zoom, map])
  useEffect(() => {
    if (focus) map.flyTo(focus, data.community.zoom, { duration: 0.75 })
  }, [focus, data.community.zoom, map])
  return null
}

export default function MapView({ data, reach, gaps, focus, newConnectionId, onMember, onInvite, onGap }: Props) {
  const members = useMemo(() => new Map(data.members.map(member => [member.id, member])), [data.members])
  const connected = useMemo(() => new Set(data.edges.flatMap(edge => [edge.a_id, edge.b_id])), [data.edges])
  const reachByCluster = useMemo(() => new Map(reach?.clusters.map(cluster => [cluster.cluster_id, cluster]) ?? []), [reach])
  const gapByCluster = useMemo(() => new Map(gaps.map(gap => [gap.cluster_id, gap])), [gaps])
  const statusMemberIds = useMemo(() => new Set(data.statuses.map(status => status.member_id)), [data.statuses])

  return (
    <MapContainer center={[data.community.center_lat, data.community.center_lng]} zoom={data.community.zoom} zoomControl={false} className="map-container" scrollWheelZoom={false}>
      <TileLayer
        className="dusk-tiles"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FlyTo data={data} focus={focus} />
      {data.clusters.map(cluster => {
        const positions = cluster.polygon.coordinates[0]?.map(([lng, lat]) => [lat, lng] as LatLngExpression) ?? []
        const clusterReach = reachByCluster.get(cluster.id)
        const gap = gapByCluster.get(cluster.id)
        return (
          <Polygon
            key={cluster.id}
            positions={positions}
            pathOptions={{ color: clusterColor(clusterReach?.ratio ?? 0), weight: gap ? 3 : 1.5, opacity: gap ? 0.9 : 0.5, fillColor: clusterColor(clusterReach?.ratio ?? 0), fillOpacity: gap ? 0.38 : 0.2 }}
            eventHandlers={{ click: () => gap && onGap(gap) }}
          >
            <Tooltip direction="top" sticky>
              {cluster.name} · {clusterReach?.met ?? 0} of {clusterReach?.total ?? 0} met
            </Tooltip>
          </Polygon>
        )
      })}
      {data.edges.map(edge => {
        const a = members.get(edge.a_id)
        const b = members.get(edge.b_id)
        if (!a || !b) return null
        return (
          <Polyline
            key={`${edge.a_id}-${edge.b_id}`}
            positions={[[a.lat, a.lng], [b.lat, b.lng]]}
            pathOptions={{ color: theme.color.amber, weight: 1.5 + 5 * Math.min(edge.strength, 3) / 3, opacity: Math.min(0.92, 0.45 + 0.09 * edge.hangout_count), className: edge.a_id === newConnectionId || edge.b_id === newConnectionId ? 'new-connection' : '' }}
          />
        )
      })}
      {data.members.map(member => (
        <Marker
          key={member.id}
          position={[member.lat, member.lng]}
          icon={icon(member.is_demo_user ? '✦' : member.emoji_avatar, `member-pin ${member.is_demo_user ? 'you-pin' : connected.has(member.id) ? 'connected-pin' : 'unmet-pin'}`, member.is_demo_user ? 52 : 40)}
          eventHandlers={{ click: () => !member.is_demo_user && onMember(member) }}
        >
          <Tooltip direction="top" offset={[0, -20]}>{member.is_demo_user ? 'You' : member.display_name}{statusMemberIds.has(member.id) ? ' · free to hang out' : ''}</Tooltip>
        </Marker>
      ))}
      {data.statuses.map(status => {
        const member = members.get(status.member_id)
        if (!member) return null
        return (
          <Marker key={status.id} position={[member.lat + 0.00012, member.lng + 0.00012]} icon={icon('●', 'status-pin', 22)} eventHandlers={{ click: () => onMember(member) }}>
            <Tooltip direction="top">{member.display_name}: {status.text}</Tooltip>
          </Marker>
        )
      })}
      {data.invites.filter(invite => invite.status === 'open').map(invite => (
        <Marker key={invite.id} position={[invite.lat, invite.lng]} icon={icon('✦', 'invite-pin', 36)} eventHandlers={{ click: () => onInvite(invite) }}>
          <Tooltip direction="top">{invite.title}</Tooltip>
        </Marker>
      ))}
    </MapContainer>
  )
}

import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Invite, ParsedInvite, PublicMember } from './api'
import { api } from './api'
import MapView from './MapView'
import BottomSheet from './BottomSheet'

type Sheet = 'nudge' | 'composer' | 'sent' | 'voice' | 'invite' | null
type Tone = 'casual' | 'warmer' | 'shorter'

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

function localDateTime(value: string): string {
  const date = new Date(value)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function useAnimatedCount(target: number, resetKey: string, ready: boolean): number {
  const [value, setValue] = useState(target)
  const previous = useRef(target)
  const readyRef = useRef(false)
  const keyRef = useRef(resetKey)
  useEffect(() => {
    if (keyRef.current !== resetKey) {
      keyRef.current = resetKey
      readyRef.current = false
    }
    if (!ready) return
    if (!readyRef.current) {
      readyRef.current = true
      previous.current = target
      setValue(target)
      return
    }
    const from = previous.current
    if (from === target) return
    previous.current = target
    const start = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / 850)
      setValue(Math.round(from + (target - from) * (1 - Math.pow(1 - progress, 3))))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, resetKey, ready])
  return value
}

export default function App() {
  const queryClient = useQueryClient()
  const communitiesQuery = useQuery({ queryKey: ['communities'], queryFn: api.communities })
  const [communityId, setCommunityId] = useState('hydepark')
  const [sheet, setSheet] = useState<Sheet>(null)
  const [tone, setTone] = useState<Tone>('casual')
  const [draftText, setDraftText] = useState('')
  const [selectedInvite, setSelectedInvite] = useState<Invite | null>(null)
  const [selectedMember, setSelectedMember] = useState<PublicMember | null>(null)
  const [focus, setFocus] = useState<[number, number]>()
  const [newConnectionId, setNewConnectionId] = useState<string>()
  const [degraded, setDegraded] = useState(false)
  const [notice, setNotice] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [recording, setRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [voicePreview, setVoicePreview] = useState<{ transcript: string; parsed: ParsedInvite }>()
  const [voiceForm, setVoiceForm] = useState({ title: '', activity: '', starts_at: '', capacity: 4, place_hint: '' })
  const recorder = useRef<MediaRecorder | null>(null)
  const recordTimer = useRef<number | null>(null)
  const recordDeadline = useRef<number | null>(null)
  const cancelRecording = useRef(false)
  const initialCameraSet = useRef(false)

  const mapQuery = useQuery({ queryKey: ['map', communityId], queryFn: () => api.map(communityId) })
  const reachQuery = useQuery({ queryKey: ['reach', communityId], queryFn: () => api.reach(communityId) })
  const gapsQuery = useQuery({ queryKey: ['gaps', communityId], queryFn: () => api.gaps(communityId) })
  const nudgeQuery = useQuery({ queryKey: ['nudge', communityId, 'small_ask'], queryFn: () => api.nudge(communityId, 'small_ask'), enabled: sheet === 'nudge' })

  useEffect(() => { if (nudgeQuery.data?.degraded) setDegraded(true) }, [nudgeQuery.data?.degraded])
  useEffect(() => {
    if (initialCameraSet.current || communityId !== 'hydepark') return
    const demoMember = mapQuery.data?.members.find(member => member.is_demo_user)
    const firstGap = gapsQuery.data?.gaps[0]
    const gapCluster = mapQuery.data?.clusters.find(cluster => cluster.id === firstGap?.cluster_id)
    if (!demoMember || !gapCluster) return
    const points = gapCluster.polygon.coordinates[0]
    const gapLat = points.reduce((sum, point) => sum + point[1], 0) / points.length
    const gapLng = points.reduce((sum, point) => sum + point[0], 0) / points.length
    initialCameraSet.current = true
    setFocus([(demoMember.lat + gapLat) / 2 + 0.0015, (demoMember.lng + gapLng) / 2])
  }, [communityId, mapQuery.data, gapsQuery.data])

  const draftMutation = useMutation({
    mutationFn: (nextTone: Tone) => api.draft({ community_id: communityId, to_id: nudgeQuery.data!.candidate.id, context: nudgeQuery.data!.nudge.first_step, tone: nextTone }),
    onSuccess: draft => { setDraftText(draft.text); setSelectedMember(draft.to_member); setDegraded(previous => previous || draft.degraded); setSheet('composer') },
  })
  const sendMutation = useMutation({
    mutationFn: () => api.send(draftMutation.data!.id, draftText.trim()),
    onSuccess: () => setSheet('sent'),
  })
  const hangoutMutation = useMutation({
    mutationFn: () => api.hangout(communityId, selectedMember!.id),
    onSuccess: result => {
      setNewConnectionId(selectedMember!.id)
      queryClient.setQueryData(['reach', communityId], result.after)
      queryClient.invalidateQueries({ queryKey: ['map', communityId] })
      queryClient.invalidateQueries({ queryKey: ['gaps', communityId] })
      setSheet(null)
      setNotice(`You reached one more neighbor in ${result.after.clusters.find(cluster => cluster.cluster_id === selectedMember?.cluster_id)?.name ?? 'your community'}.`)
    },
  })
  const voiceMutation = useMutation({
    mutationFn: (audio: Blob) => api.voice(communityId, audio),
    onSuccess: response => {
      setVoicePreview({ transcript: response.transcript, parsed: response.parsed })
      setVoiceForm({ title: response.parsed.title, activity: response.parsed.activity, starts_at: localDateTime(response.parsed.starts_at), capacity: response.parsed.capacity, place_hint: response.parsed.place_hint })
      setDegraded(previous => previous || response.degraded)
    },
  })
  const inviteMutation = useMutation({
    mutationFn: () => api.invite({ community_id: communityId, title: voiceForm.title.trim(), activity: voiceForm.activity.trim(), starts_at: new Date(voiceForm.starts_at).toISOString(), capacity: Number(voiceForm.capacity), place_hint: voiceForm.place_hint.trim(), requires_approval: true, source: 'voice' }),
    onSuccess: invite => {
      setVoicePreview(undefined)
      setSheet(null)
      setSelectedInvite(invite)
      setFocus([invite.lat, invite.lng])
      setNotice('Your invite is on the map.')
      queryClient.invalidateQueries({ queryKey: ['map', communityId] })
    },
  })
  const resetMutation = useMutation({
    mutationFn: api.reset,
    onSuccess: () => {
      queryClient.invalidateQueries()
      setNewConnectionId(undefined)
      setNotice('Demo reset. The map is ready for a fresh hello.')
      setSettingsOpen(false)
      setSheet(null)
    },
  })

  const stopRecording = () => {
    if (recordTimer.current !== null) window.clearInterval(recordTimer.current)
    if (recordDeadline.current !== null) window.clearTimeout(recordDeadline.current)
    recordTimer.current = null
    recordDeadline.current = null
    if (recorder.current?.state === 'recording') recorder.current.stop()
    setRecording(false)
  }

  const startRecording = async () => {
    setNotice('')
    setVoicePreview(undefined)
    voiceMutation.reset()
    cancelRecording.current = false
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setNotice('Audio recording needs a supported browser and a secure connection.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const chunks: BlobPart[] = []
      const preferred = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm']
      const mimeType = preferred.find(type => MediaRecorder.isTypeSupported(type))
      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      recorder.current = mediaRecorder
      mediaRecorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data) }
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop())
        if (!cancelRecording.current && chunks.length) voiceMutation.mutate(new Blob(chunks, { type: mediaRecorder.mimeType }))
      }
      mediaRecorder.start()
      setRecordingSeconds(0)
      setRecording(true)
      const started = Date.now()
      recordTimer.current = window.setInterval(() => setRecordingSeconds(Math.min(15, Math.floor((Date.now() - started) / 1000))), 200)
      recordDeadline.current = window.setTimeout(stopRecording, 15_000)
    } catch {
      setNotice('Microphone access was unavailable. Please allow it and try again.')
    }
  }

  const closeSheet = () => {
    if (recording) { cancelRecording.current = true; stopRecording() }
    setSheet(null)
  }

  const switchCommunity = (id: string) => {
    if (id === communityId) return
    if (recording) { cancelRecording.current = true; stopRecording() }
    setCommunityId(id)
    setSheet(null)
    setSelectedInvite(null)
    setSelectedMember(null)
    setFocus(undefined)
    setNotice('')
    setNewConnectionId(undefined)
    setDegraded(false)
  }

  const map = mapQuery.data
  const reach = reachQuery.data
  const gap = gapsQuery.data?.gaps[0]
  const animatedMet = useAnimatedCount(reach?.met ?? 0, communityId, Boolean(reach))
  const loadingMap = communitiesQuery.isPending || mapQuery.isPending || reachQuery.isPending || gapsQuery.isPending
  const loadError = communitiesQuery.error ?? mapQuery.error ?? reachQuery.error ?? gapsQuery.error
  const displayedCommunities = communitiesQuery.data?.communities ?? []
  const inviteHost = map?.members.find(member => member.id === selectedInvite?.host_id)

  return (
    <main className="app-shell">
      {map && <MapView data={map} reach={reach} gaps={gapsQuery.data?.gaps ?? []} focus={focus} newConnectionId={newConnectionId} onMember={member => { setSelectedMember(member); setFocus([member.lat, member.lng]); setNotice(`${member.display_name} · ${member.interests.slice(0, 2).join(', ')}`) }} onInvite={invite => { setSelectedInvite(invite); setSheet('invite') }} onGap={selectedGap => { const cluster = map.clusters.find(item => item.id === selectedGap.cluster_id); if (cluster) { const points = cluster.polygon.coordinates[0]; setFocus([points.reduce((sum, point) => sum + point[1], 0) / points.length, points.reduce((sum, point) => sum + point[0], 0) / points.length]) }; setSheet('nudge') }} />}
      {loadingMap && <div className="map-loading"><div className="lantern-loading">✦</div><p>Lighting up the neighborhood…</p></div>}
      {loadError && <div className="error-screen"><span className="lantern-logo">✦</span><h1>Couldn’t load the map</h1><p>{loadError.message}</p><button className="primary-button" onClick={() => queryClient.invalidateQueries()}>Try again</button></div>}

      <header className="topbar">
        <div className="brand"><span className="brand-mark">✦</span><span>Porchlight</span></div>
        <div className="header-actions">
          {degraded && <span className="degraded-badge">Offline mode</span>}
          <button className="settings-button" aria-label="Settings" aria-expanded={settingsOpen} onClick={() => setSettingsOpen(value => !value)}>•••</button>
        </div>
      </header>

      <div className="community-switch" role="group" aria-label="Community">
        {displayedCommunities.map(community => (
          <button key={community.id} className={community.id === communityId ? 'active' : ''} aria-pressed={community.id === communityId} onClick={() => switchCommunity(community.id)}>{community.name === 'The Quarry Lofts' ? 'Quarry Lofts' : community.name}</button>
        ))}
      </div>

      {settingsOpen && <div className="settings-menu"><span className="eyebrow">DEMO TOOLS</span><button onClick={() => resetMutation.mutate()} disabled={resetMutation.isPending}>{resetMutation.isPending ? 'Resetting…' : 'Reset demo'}</button></div>}

      {reach && <div className="reach-chip" aria-live="polite"><span className="reach-label">Reach</span><strong>You’ve met <em>{animatedMet}</em> of {reach.total}</strong></div>}
      {gap && sheet === null && <div className="gap-card"><div><span className="eyebrow">A PLACE TO START</span><h2>{gap.name} <span>· {Math.round(gap.reach * 100)}% reached</span></h2><p>There are {gap.size} neighbors nearby you haven’t met yet.</p></div><button className="gap-action" onClick={() => setSheet('nudge')}>See Muse’s idea <span aria-hidden="true">↗</span></button></div>}
      {sheet === null && <button className="mic-fab" aria-label="Create a voice invite" onClick={() => { setVoicePreview(undefined); setSheet('voice') }}><span aria-hidden="true">🎙</span></button>}
      {notice && <div className="toast" role="status">{notice}<button aria-label="Dismiss" onClick={() => setNotice('')}>×</button></div>}

      {sheet === 'nudge' && <BottomSheet title="Muse nudge" onClose={closeSheet}>
        <div className="sheet-icon">✦</div>
        {nudgeQuery.isPending ? <div className="skeleton-group" aria-live="polite"><h2>Muse is thinking…</h2><div className="skeleton wide" /><div className="skeleton" /><div className="skeleton short" /></div> : nudgeQuery.error ? <div className="sheet-error"><h2>Couldn’t get a nudge</h2><p>{nudgeQuery.error.message}</p><button className="secondary-button" onClick={() => nudgeQuery.refetch()}>Try again</button></div> : nudgeQuery.data && <>
          <h2>{nudgeQuery.data.nudge.headline}</h2>
          <div className="neighbor-card"><span className="avatar large">{nudgeQuery.data.candidate.emoji_avatar}</span><div><strong>{nudgeQuery.data.candidate.display_name}</strong><p>{nudgeQuery.data.nudge.why}</p></div></div>
          <p className="first-step"><span>First step</span>{nudgeQuery.data.nudge.first_step}</p>
          <button className="primary-button full" onClick={() => { setTone('casual'); draftMutation.mutate('casual') }} disabled={draftMutation.isPending}>{draftMutation.isPending ? 'Muse is drafting…' : 'Draft a hello'}</button>
          {draftMutation.error && <p className="error-text">{draftMutation.error.message}</p>}
        </>}
      </BottomSheet>}

      {sheet === 'composer' && draftMutation.data && <BottomSheet title="Message composer" onClose={closeSheet}>
        <span className="eyebrow">DRAFTED BY MUSE — EDIT ANYTHING</span>
        <h2>Your first hello</h2>
        <div className="recipient"><span className="avatar">{draftMutation.data.to_member.emoji_avatar}</span><span>To: <strong>{draftMutation.data.to_member.display_name}</strong></span></div>
        <label className="field-label" htmlFor="draft-text">Your message</label>
        <textarea id="draft-text" className="composer-textarea" value={draftText} maxLength={1000} onChange={event => setDraftText(event.target.value)} />
        <div className="tone-row" role="group" aria-label="Draft tone">{(['casual', 'warmer', 'shorter'] as Tone[]).map(option => <button key={option} className={tone === option ? 'selected' : ''} onClick={() => { setTone(option); draftMutation.mutate(option) }} disabled={draftMutation.isPending}>{option[0].toUpperCase() + option.slice(1)}</button>)}</div>
        <p className="helper-copy">You can edit this before sending. Your choice is final.</p>
        <button className="primary-button full" disabled={!draftText.trim() || sendMutation.isPending || draftMutation.isPending} onClick={() => sendMutation.mutate()}>{sendMutation.isPending ? 'Sending…' : 'Send'}</button>
        {sendMutation.error && <p className="error-text">{sendMutation.error.message}</p>}
      </BottomSheet>}

      {sheet === 'sent' && selectedMember && <BottomSheet title="Hello sent" onClose={closeSheet}>
        <div className="sheet-icon">✦</div><h2>One hello closer.</h2><p className="sheet-copy">Your message to {selectedMember.display_name} was recorded for this demo. When you meet in person, add that connection to your map.</p>
        <button className="primary-button full" disabled={hangoutMutation.isPending} onClick={() => hangoutMutation.mutate()}>{hangoutMutation.isPending ? 'Updating Reach…' : 'Mark as met'}</button>
        <button className="text-button full" onClick={closeSheet}>Maybe later</button>
        {hangoutMutation.error && <p className="error-text">{hangoutMutation.error.message}</p>}
      </BottomSheet>}

      {sheet === 'voice' && <BottomSheet title="Voice post" onClose={closeSheet} tall>
        <span className="eyebrow">MAKE AN INVITE</span><h2>Say it out loud.</h2><p className="sheet-copy">A short voice note can become a map pin. You’ll review everything before it posts.</p>
        {voicePreview ? <>
          <div className="transcript-card"><span className="eyebrow">TRANSCRIPT</span><p>“{voicePreview.transcript}”</p></div>
          <span className="eyebrow form-heading">DETECTION RESULTS — EDIT ANYTHING</span>
          <div className="voice-fields"><label>Title<input value={voiceForm.title} onChange={event => setVoiceForm({ ...voiceForm, title: event.target.value })} /></label><label>Activity<input value={voiceForm.activity} onChange={event => setVoiceForm({ ...voiceForm, activity: event.target.value })} /></label><label>Time<input type="datetime-local" value={voiceForm.starts_at} onChange={event => setVoiceForm({ ...voiceForm, starts_at: event.target.value })} /></label><label>Spots<input type="number" min="1" max="100" value={voiceForm.capacity} onChange={event => setVoiceForm({ ...voiceForm, capacity: Number(event.target.value) })} /></label><label>Near<input value={voiceForm.place_hint} onChange={event => setVoiceForm({ ...voiceForm, place_hint: event.target.value })} /></label></div>
          <p className="privacy-copy">📍 Share a nearby landmark, not a home address. Location is shared after host approval.</p>
          <button className="primary-button full" disabled={inviteMutation.isPending || !voiceForm.title.trim() || !voiceForm.activity.trim() || !voiceForm.place_hint.trim() || !voiceForm.starts_at || voiceForm.capacity < 1 || voiceForm.capacity > 100} onClick={() => inviteMutation.mutate()}>{inviteMutation.isPending ? 'Posting…' : 'Post to map'}</button>
          {inviteMutation.error && <p className="error-text">{inviteMutation.error.message}</p>}
          <button className="text-button full" onClick={startRecording}>Record again</button>
        </> : <>
          <div className={`voice-stage ${recording ? 'is-recording' : ''}`}><div className="wave" aria-hidden="true"><i /><i /><i /><i /><i /></div><button className="voice-record-button" aria-label={recording ? 'Stop recording' : 'Start recording'} onClick={recording ? stopRecording : startRecording}>{recording ? '■' : '🎙'}</button><div className="wave" aria-hidden="true"><i /><i /><i /><i /><i /></div></div>
          <p className="record-instruction">{recording ? `Recording ${recordingSeconds} / 15 seconds · Tap to stop` : voiceMutation.isPending ? 'Muse is transcribing and finding the details…' : 'Tap the microphone to record up to 15 seconds.'}</p>
          {voiceMutation.isPending && <div className="skeleton-group"><div className="skeleton wide" /><div className="skeleton" /><div className="skeleton short" /></div>}
          {voiceMutation.error && <p className="error-text">{voiceMutation.error.message}</p>}
        </>}
      </BottomSheet>}

      {sheet === 'invite' && selectedInvite && <BottomSheet title="Invite detail" onClose={closeSheet}>
        <span className="invite-tag">✦ {selectedInvite.activity}</span><h2>{selectedInvite.title}</h2>
        <div className="spots-pill">{Math.max(0, selectedInvite.capacity - selectedInvite.going_count)} of {selectedInvite.capacity} spots left</div>
        <div className="invite-facts"><span>◷ {dateLabel(selectedInvite.starts_at)}</span><span>⌖ {selectedInvite.place_hint}</span></div>
        <div className="neighbor-card host-card"><span className="avatar large">{inviteHost?.emoji_avatar ?? '🏡'}</span><div><strong>Host: {inviteHost?.display_name ?? 'Your neighbor'}</strong><p>{inviteHost?.verified ? '✓ Verified neighbor' : 'Neighbor'}</p></div></div>
        <p className="privacy-copy">🔒 Location shared after host approves.</p>
      </BottomSheet>}
    </main>
  )
}

# Quality Gates

## Reliability
- No stuck keys after crash/restart (release-all on shutdown)
- Hotplug safe: device disconnect/reconnect recovers
- Wayland-safe: no compositor dependencies for remap

## Performance
- Input processing overhead: target <1ms average per event
- Profile switch latency: <250ms

## UX
- Onboarding gets to first working bind fast
- Clear error messages for permission issues
- Import/export profiles

## Test plan
- Unit tests for key mapping coverage
- Synthetic event tests for layer switching correctness
- Smoke test scripts for common mice/keyboards

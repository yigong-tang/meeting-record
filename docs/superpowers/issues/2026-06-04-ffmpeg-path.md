# ffmpeg PATH 问题

**状态：** 待验证（下次重启后）

**问题：**
winget 安装 ffmpeg 后，Git Bash 中 `ffmpeg` 命令不可用，需手动 export 绝对路径。
PowerShell/CMD 重启后理论上生效，但尚未验证。

**当前 workaround：**
```bash
export PATH="$LOCALAPPDATA/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin:$PATH"
```

**yt-dlp 行为：**
- ffmpeg 可用 → 自动合并音视频流
- ffmpeg 不可用 → 分别下载音视频文件（.mp4 + .m4a），不合并
- meeting-cli download 命令会预先检查并警告

**下次验证：**
- [ ] 重启后 PowerShell 中 `ffmpeg -version` 是否可用
- [ ] 重启后 Git Bash 中 `ffmpeg -version` 是否可用
- [ ] meeting-cli download 是否能自动合并音视频流

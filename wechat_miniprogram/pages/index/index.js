// pages/index/index.js
const app = getApp()

Page({
  data: {
    serverStatus: 'unknown',
    aiModels: [],
    connectionCount: 0,
    userInfo: {},
    hasUserInfo: false,
    canIUseGetUserProfile: false,
    canIUseOpenData: wx.canIUse('open-data.type.userAvatarUrl')
  },

  onLoad() {
    if (wx.getUserProfile) {
      this.setData({
        canIUseGetUserProfile: true
      })
    }
    
    // 检查服务器状态
    this.checkServerStatus()
  },
  
  onShow() {
    this.checkServerStatus()
  },
  
  onPullDownRefresh() {
    this.checkServerStatus().then(() => {
      wx.stopPullDownRefresh()
    })
  },
  
  // 检查服务器状态
  checkServerStatus() {
    return app.checkServerStatus().then(data => {
      this.setData({
        serverStatus: 'healthy',
        connectionCount: data.connectionCount || 0
      })
      wx.showToast({
        title: '服务器连接正常',
        icon: 'success',
        duration: 1000
      })
    }).catch(err => {
      this.setData({
        serverStatus: 'unhealthy'
      })
      wx.showToast({
        title: '服务器连接失败',
        icon: 'none',
        duration: 2000
      })
    })
  },
  
  // 获取用户信息
  getUserProfile() {
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        this.setData({
          userInfo: res.userInfo,
          hasUserInfo: true
        })
      }
    })
  },
  
  // 跳转到AI对话页面
  gotoChat() {
    wx.navigateTo({
      url: '/pages/chat/chat'
    })
  },
  
  // 跳转到指令控制页面
  gotoCommands() {
    wx.navigateTo({
      url: '/pages/commands/commands'
    })
  },
  
  // 跳转到设置页面
  gotoSettings() {
    wx.navigateTo({
      url: '/pages/settings/settings'
    })
  },
  
  // 快速指令
  quickCommand(e) {
    const command = e.currentTarget.dataset.command
    wx.showModal({
      title: '确认执行',
      content: `确定要执行指令: ${command} 吗？`,
      success: (res) => {
        if (res.confirm) {
          this.executeQuickCommand(command)
        }
      }
    })
  },
  
  // 执行快速指令
  executeQuickCommand(command) {
    wx.showLoading({
      title: '执行中...'
    })
    
    if (command.startsWith('sys:')) {
      app.sendSystemCommand(command.replace('sys:', '')).then(result => {
        wx.hideLoading()
        wx.showModal({
          title: '系统指令结果',
          content: result.result || '指令执行完成',
          showCancel: false
        })
      }).catch(err => {
        wx.hideLoading()
        wx.showToast({
          title: '执行失败',
          icon: 'none'
        })
      })
    } else {
      app.sendAICommand(command).then(result => {
        wx.hideLoading()
        wx.showModal({
          title: 'AI回复',
          content: result.result || '指令执行完成',
          showCancel: false
        })
      }).catch(err => {
        wx.hideLoading()
        wx.showToast({
          title: '执行失败',
          icon: 'none'
        })
      })
    }
  }
})
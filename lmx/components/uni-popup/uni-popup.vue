<template>
  <view class="uni-popup" :class="[popupClass]" @touchmove.stop.prevent="clear">
    <view v-if="maskShow" class="uni-popup-mask" :class="[maskClass]" @tap="onTap"></view>
    <view class="uni-popup-wrapper" :class="[position, wrapperClass]" @tap="clear">
      <view class="uni-popup-content" :class="[contentClass]" @tap.stop="stopEvent">
        <slot></slot>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'UniPopup',
  props: {
    // 开启动画
    animation: {
      type: Boolean,
      default: true
    },
    // 弹出层类型，可选值：top/bottom/center
    type: {
      type: String,
      default: 'center'
    },
    // maskClick
    maskClick: {
      type: Boolean,
      default: true
    },
    backgroundColor: {
      type: String,
      default: 'none'
    }
  },
  data() {
    return {
      duration: 300,
      ani: [],
      showPopup: false,
      showTrans: false,
      maskClass: {
        'position': 'fixed',
        'bottom': 0,
        'top': 0,
        'left': 0,
        'right': 0,
        'backgroundColor': 'rgba(0, 0, 0, 0.4)'
      },
      popupClass: {
        'position': 'fixed',
        'left': 0,
        'right': 0,
      },
      wrapperClass: {},
      contentClass: {}
    }
  },
  computed: {
    // 弹窗位置
    position() {
      return 'uni-popup-' + this.type
    },
    // 遮罩显示
    maskShow() {
      return this.showPopup
    }
  },
  created() {
    // this.mkclick = true;
    if (this.animation) {
      this.duration = 300;
    } else {
      this.duration = 0;
    }
  },
  methods: {
    clear(e) {
      // 点击遮罩层
      if (e.target.className === 'uni-popup-wrapper') {
        if (this.maskClick) {
          this.close();
        }
      }
    },
    open() {
      this.showPopup = true;
      this.$nextTick(() => {
        setTimeout(() => {
          this.showTrans = true;
        }, 50);
      });
      this.$emit('change', {
        show: true
      });
    },
    close(type) {
      this.showTrans = false;
      this.$nextTick(() => {
        setTimeout(() => {
          this.showPopup = false;
          this.$emit('change', {
            show: false
          });
        }, 300);
      });
    },
    onTap() {
      if (!this.maskClick) return;
      this.close();
    },
    stopEvent(event) {
      event.stopPropagation();
    }
  }
}
</script>

<style scoped>
.uni-popup {
  position: fixed;
  z-index: 99;
}

.uni-popup-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.4);
  opacity: 0;
  transition-property: opacity;
  transition-duration: 0.3s;
  transition-timing-function: ease-in-out;
}

.uni-popup-mask.uni-bottom, .uni-popup-mask.uni-center, .uni-popup-mask.uni-top {
  opacity: 1;
}

.uni-popup-wrapper {
  display: block;
  position: relative;
}

.uni-popup-wrapper.uni-popup-bottom {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  transform: translateY(100%);
  transition-property: transform;
  transition-duration: 0.3s;
  transition-timing-function: ease-in-out;
}

.uni-popup-wrapper.uni-popup-bottom.uni-bottom {
  transform: translateY(0);
}

.uni-popup-content {
  position: relative;
  background-color: #fff;
  border-radius: 10px 10px 0 0;
  overflow: hidden;
}

.uni-popup-content.bottom {
  border-top-left-radius: 10px;
  border-top-right-radius: 10px;
}
</style> 
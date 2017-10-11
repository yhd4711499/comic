/**
 * Created by Ornithopter on 2017/10/8.
 */
import React from "react";
import {ListItem} from "material-ui/List";

class ComicCell extends React.Component {
    constructor(props) {
        super(props);
    }

    fuzzyFacebookTime(timeValue, options) {

        const defaultOptions = {
            // time display options
            relativeTime: 48,
            // language options
            monthNames: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
            amPm: ['上午', '下午'],
            ordinalSuffix: function (n) {
                // return ['th', 'st', 'nd', 'rd'][n < 4 || (n > 20 && n % 10 < 4) ? n % 10 : 0]
                return ''
            }
        };

        function parseDate(str) {
            const v = str.replace(/[T\+]/g, ' ').split(' ');
            return new Date(Date.parse(v[0] + " " + v[1] + " UTC"));
        }

        function formatTime(date, options) {
            const h = date.getHours(), m = '' + date.getMinutes(), am = options.amPm;
            return (h < 12 ? am[0] : am[1]) + (h > 12 ? h - 12 : h) + ':' + (m.length == 1 ? '0' : '' ) + m;
        }

        function formatDate(date, options) {
            const mon = options.monthNames[date.getMonth()],
                day = date.getDate(),
                year = date.getFullYear(),
                thisyear = (new Date()).getFullYear(),
                suf = options.ordinalSuffix(day);

            return (thisyear != year ? year  + '年' : '') + mon + day + '号';
        }

        options = options || defaultOptions;
        let date = parseDate(timeValue);
        let delta = parseInt(((new Date()).getTime() - date.getTime()) / 1000);
        let relative = options.relativeTime;
        let cutoff = +relative === relative ? relative * 60 * 60 : Infinity;

        if (relative === false || delta > cutoff)
            return formatDate(date, options) + formatTime(date, options);

        if (delta < 60) return '不足一分钟';
        const minutes = parseInt(delta / 60 + 0.5);
        if (minutes <= 1) return '约一分钟前';
        const hours = parseInt(minutes / 60 + 0.5);
        if (hours < 1) return minutes + ' 分钟前';
        if (hours == 1) return '约一小时前';
        const days = parseInt(hours / 24 + 0.5);
        if (days < 1) return hours + ' 小时前';
        if (days == 1) return '昨天' + formatTime(date, options);
        const weeks = parseInt(days / 7 + 0.5);
        if (weeks < 2) return days + ' 天前' + formatTime(date, options);
        const months = parseInt(weeks / 4.34812141 + 0.5);
        if (months < 2) return weeks + ' 周前';
        const years = parseInt(months / 12 + 0.5);
        if (years < 2) return months + ' 月前';
        return years + ' 年前';

    }

    render() {
        let lastUpdate;
        if (this.props.item['finished']) {
            lastUpdate = '【已完结】';
        } else {
            lastUpdate = ' 最后更新: ' + this.fuzzyFacebookTime(this.props.item['lastUpdateTime']);
        }
        return <ListItem primaryText={this.props.title} secondaryText={this.props.author + lastUpdate}/>
    }


}

export default ComicCell;
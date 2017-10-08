/**
 * Created by Ornithopter on 2017/10/8.
 */
import React from "react";
import {Link} from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import LinearProgress from "material-ui/LinearProgress";
import {List, ListItem} from "material-ui/List";

const request = require('superagent');
const superagentPromisePlugin = require('superagent-promise-plugin');
superagentPromisePlugin.Promise = require('es6-promise');


class VolumeBrowser extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            currentIndex: 0,
            showList: false,
            imageList: [],
            progress: 0
        };
        this.comic_id = this.props.match.params.comic_id;
        this.volume_id = this.props.match.params.volume_id;
        if (this.props.location.query) {
            this.all_volumes = this.props.location.query['list'];
            this.current_index = this.props.location.query['current'];
        }

        this.showNext = this.showNext.bind(this);
        this.showPrevious = this.showPrevious.bind(this);
    }

    showNext() {
        if (this.state.currentIndex + 1 >= this.state.imageList.length) {
            this.props.history.replace(`/comic/${this.comic_id}`);
        } else {
            this.setState({
                currentIndex: this.state.currentIndex + 1,
                showList: this.state.showList,
                imageList: this.state.imageList
            });
        }
    }

    showPrevious() {
        if (this.state.currentIndex - 1 < 0) {
            this.props.history.replace(`/comic/${this.comic_id}`);
        } else {
            this.setState({
                currentIndex: this.state.currentIndex - 1,
                showList: this.state.showList,
                imageList: this.state.imageList
            });
        }
    }

    loadPages() {
        const self = this;
        request.get('/api/comics/' + this.comic_id + '/' + this.volume_id)
            .use(superagentPromisePlugin)
            .then(function (res) {
                let json = JSON.parse(res.text);
                let images = json.sort((v1, v2) => {
                    return v1['index'] - v2['index']
                });
                self.setState({
                    currentIndex: self.state.currentIndex,
                    showList: self.state.showList,
                    imageList: images
                });
            })
            .catch(function (err) {
            });
    }

    componentDidMount() {
        this.loadPages();
    };

    render() {
        let elem;
        if (this.state.imageList.length == 0) {
            elem = <div>No image</div>
        } else {
            const leftStyle = {
                position: 'absolute',
                top: 0,
                left: 0,
                bottom: 0,
                width: '50%'
            };

            const rightStyle = {
                position: 'absolute',
                top: 0,
                right: 0,
                bottom: 0,
                width: '50%'
            };
            let clickRightElem;
            if (this.all_volumes != undefined && this.current_index + 1 < this.all_volumes.length) {
                let to = {
                    pathname: `/comic/${this.comic_id}/${this.all_volumes[this.current_index + 1].title}`,
                    query: {
                        list: this.all_volumes,
                        current: this.current_index + 1
                    }
                };
                clickRightElem = <Link to={to} style={rightStyle}/>
            } else {
                clickRightElem = <div onClick={this.showNext} style={rightStyle}/>
            }

            let clickLeftElem;
            if (this.all_volumes != undefined && this.current_index > 0) {
                let to = {
                    pathname: `/comic/${this.comic_id}/${this.all_volumes[this.current_index - 1].title}`,
                    query: {
                        list: this.all_volumes,
                        current: this.current_index - 1
                    }
                };
                clickLeftElem = <Link to={to} style={leftStyle}/>
            } else {
                clickLeftElem = <div onClick={this.showPrevious} style={leftStyle}/>
            }
            let imgStyle = {width: '100%', height: 'auto'};
            let bgStyle = {
                // 'background-color': 'black'
            };
            elem = <MuiThemeProvider>
                <div style={bgStyle}>
                    <LinearProgress mode="determinate" value={this.state.currentIndex + 1}
                                    max={this.state.imageList.length}/>
                    <label>{this.volume_id}</label>
                    <div>
                        <img src={this.state.imageList[this.state.currentIndex]['url']} style={imgStyle}/>
                    </div>
                    {clickLeftElem}
                    {clickRightElem}
                </div>
            </MuiThemeProvider>
        }
        return <div>{elem}</div>
    }

}

export default VolumeBrowser
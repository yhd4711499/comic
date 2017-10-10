/**
 * Created by Ornithopter on 2017/10/8.
 */
import React from "react";
import {Link} from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import LinearProgress from "material-ui/LinearProgress";
import {List, ListItem} from "material-ui/List";
import AppBar from "material-ui/AppBar";
import IconButton from "material-ui/IconButton";
import NavigationBack from "material-ui/svg-icons/navigation/arrow-back";
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
            progress: 0,
            volumeTitle: "",
            comic_id: this.props.match.params.comic_id,
            volume_id: this.props.match.params.volume_id
        };

        this.showNext = this.showNext.bind(this);
        this.showPrevious = this.showPrevious.bind(this);
    }

    showNext() {
        const self = this;
        if (this.state.currentIndex + 1 >= this.state.imageList.length) {
            request.get('/api/comics/next/' + this.state.comic_id + '/' + this.state.volume_id)
                .use(superagentPromisePlugin)
                .then(function (res) {
                    let json = JSON.parse(res.text);
                    if (json['id'] != undefined) {
                        let images = json['images'].sort((v1, v2) => {
                            return v1['index'] - v2['index']
                        });
                        self.setState({
                            currentIndex: 0,
                            showList: self.state.showList,
                            imageList: images,
                            volumeTitle: json['title'],
                            comic_id: self.state.comic_id,
                            volume_id: json['id']
                        });
                        self.props.history.replace(`/comic/${self.state.comic_id}/${json['id']}`);
                    } else {
                        self.props.history.replace(`/comic/${self.state.comic_id}`);
                    }
                })
                .catch(function (err) {
                    alert(err);
                });

        } else {
            this.setState({
                currentIndex: this.state.currentIndex + 1,
                showList: this.state.showList,
                imageList: this.state.imageList,
                volumeTitle: this.state.volumeTitle,
                comic_id: this.state.comic_id,
                volume_id: this.state.volume_id
            });
        }
    }

    showPrevious() {
        const self = this;
        if (this.state.currentIndex - 1 < 0) {
            request.get('/api/comics/previous/' + this.state.comic_id + '/' + this.state.volume_id)
                .use(superagentPromisePlugin)
                .then(function (res) {
                    let json = JSON.parse(res.text);
                    if (json.hasOwnProperty('id')) {
                        let images = json['images'].sort((v1, v2) => {
                            return v1['index'] - v2['index']
                        });
                        self.setState({
                            currentIndex: images.length - 1,
                            showList: self.state.showList,
                            imageList: images,
                            volumeTitle: json['title'],
                            comic_id: self.state.comic_id,
                            volume_id: json['id']
                        });
                        self.props.history.replace(`/comic/${self.state.comic_id}/${json['id']}`);
                    } else {
                        self.props.history.replace(`/comic/${self.state.comic_id}`);
                    }
                })
                .catch(function (err) {
                    alert(err);
                });
        } else {
            this.setState({
                currentIndex: this.state.currentIndex - 1,
                showList: this.state.showList,
                imageList: this.state.imageList,
                volumeTitle: this.state.volumeTitle,
                comic_id: this.state.comic_id,
                volume_id: this.state.volume_id
            });
        }
    }

    loadPages() {
        const self = this;
        request.get('/api/comics/' + this.state.comic_id + '/' + this.state.volume_id)
            .use(superagentPromisePlugin)
            .then(function (res) {
                let json = JSON.parse(res.text);
                let images = json['images'].sort((v1, v2) => {
                    return v1['index'] - v2['index']
                });
                self.setState({
                    currentIndex: 0,
                    showList: self.state.showList,
                    imageList: images,
                    volumeTitle: json['title'],
                    comic_id: self.state.comic_id,
                    volume_id: json['id']
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
            let clickRightElem = <div onClick={this.showNext} style={rightStyle}/>;
            let clickLeftElem = <div onClick={this.showPrevious} style={leftStyle}/>;
            let imgStyle = {width: '100%', height: 'auto'};
            let bgStyle = {
                // 'background-color': 'black'
            };
            elem = <MuiThemeProvider>
                <div style={bgStyle}>
                    <AppBar
                        title={this.state.volumeTitle}
                        iconElementLeft={<IconButton><NavigationBack onClick={this.props.history.goBack}/></IconButton>}
                    />

                    <LinearProgress mode="determinate" value={this.state.currentIndex + 1}
                                    max={this.state.imageList.length}/>
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
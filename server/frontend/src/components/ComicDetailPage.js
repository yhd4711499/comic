/**
 * Created by Ornithopter on 2017/10/8.
 */
import React from "react";
import {Link} from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import {List, ListItem} from "material-ui/List";

const request = require('superagent');
const superagentPromisePlugin = require('superagent-promise-plugin');
superagentPromisePlugin.Promise = require('es6-promise');

class VolumeCell extends React.Component {
    constructor(props) {
        super(props);
    }

    render() {
        return <ListItem primaryText={this.props.title}/>
    }
}

class ComicDetailPage extends React.Component {
    constructor(props) {
        super(props);
        this.state = {volumes: []};
        this.comic_id = this.props.match.params.comic_id;
        this.updateVolumes = this.updateVolumes.bind(this);
    }

    updateVolumes(volumes) {
        this.setState({volumes: volumes});
    }

    loadVolumes() {
        const self = this;
        request.get('/api/comics/' + this.comic_id)
            .use(superagentPromisePlugin)
            .then(function (res) {
                let json = JSON.parse(res.text);
                self.updateVolumes(json);
            })
            .catch(function (err) {
            });
    };

    componentDidMount() {
        this.loadVolumes()
    };

    getTo(i) {
        const volumes = this.state.volumes;
        const pathname = `/comic/${this.comic_id}/${volumes[i].title}`;
        const query = {
            list: volumes,
            current: i
        };
        return {
            pathname: pathname,
            // query: query
        }
    }

    render() {
        const volumes = this.state.volumes;
        if (this.state.volumes.length == 0) {
            return <div/>
        } else {
            return <MuiThemeProvider>
                <List>
                    {[...new Array(this.state.volumes.length)].map((x, i) =>
                        <Link to={this.getTo(i)}>
                            <VolumeCell title={volumes[i].title}/>
                        </Link>
                    )}
                </List>
            </MuiThemeProvider>
        }
    }
}

export default ComicDetailPage
/**
 * Created by Ornithopter on 2017/10/8.
 */
import React from "react";
import {Link} from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import {List, ListItem} from "material-ui/List";
import AppBar from 'material-ui/AppBar';
import IconButton from 'material-ui/IconButton';
import NavigationBack from 'material-ui/svg-icons/navigation/arrow-back';

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
        this.state = {
            volumes: [],
            comic_info: {}
        };
        this.comic_id = this.props.match.params.comic_id;
    }

    loadVolumes() {
        const self = this;
        request.get('/api/comics/' + this.comic_id)
            .use(superagentPromisePlugin)
            .then(function (res) {
                let json = JSON.parse(res.text);
                self.setState({
                    volumes: json['volumes'],
                    comic_info: json['comic_info']
                });
            })
            .catch(function (err) {
            });
    };

    componentDidMount() {
        this.loadVolumes()
    };

    getTo(i) {
        const volumes = this.state.volumes;
        const pathname = `/comic/${this.comic_id}/${volumes[i].id}`;
        return {
            pathname: pathname
        }
    }

    render() {
        const volumes = this.state.volumes;
        if (this.state.volumes.length == 0) {
            return <div/>
        } else {
            return <MuiThemeProvider>
                <div>
                    <AppBar
                        title={'Comic: ' + this.state.comic_info['title']}
                        iconElementLeft={<IconButton><NavigationBack onClick={this.props.history.goBack}/></IconButton>}
                    />
                    <List>
                        {[...new Array(this.state.volumes.length)].map((x, i) =>
                            <Link key={volumes[i].id} to={this.getTo(i)}>
                                <VolumeCell title={volumes[i].title}/>
                            </Link>
                        )}
                    </List>
                </div>
            </MuiThemeProvider>
        }
    }
}

export default ComicDetailPage
/**
 * Created by Ornithopter on 2017/10/8.
 */
import React from "react";
import {Link} from "react-router-dom";
import MuiThemeProvider from "material-ui/styles/MuiThemeProvider";
import {List, ListItem} from "material-ui/List";
import AppBar from "material-ui/AppBar";
import IconButton from "material-ui/IconButton";
import NavigationMenu from "material-ui/svg-icons/navigation/menu";
import ComicCell from "./ComicCell";
import AutoComplete from "material-ui/AutoComplete";

const request = require('superagent');
const superagentPromisePlugin = require('superagent-promise-plugin');

superagentPromisePlugin.Promise = require('es6-promise');

class AllComics extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            comics: [],
        };
        this.loadComics = this.loadComics.bind(this);
        this.onNewRequest = this.onNewRequest.bind(this);
    }

    onNewRequest(str, index) {
        this.props.history.push(`/comic/${this.state.comics[index].source.id}`)
    };

    loadComics() {
        const self = this;
        request.get('/api/comics/all')
            .use(superagentPromisePlugin)
            .then(function (res) {
                let json = JSON.parse(res.text);
                self.setState({
                    comics: json.sort((v1, v2) => {
                        return v2['lastUpdateTime'].localeCompare(v1['lastUpdateTime'])
                    }),
                    dataSource: json
                });
            })
            .catch(function (err) {

            });
    }

    render() {
        return <MuiThemeProvider>
            <div>
                <AppBar
                    title='Comics'
                    iconElementLeft={<IconButton><NavigationMenu /></IconButton>}
                />
                <AutoComplete
                    hintText="Search"
                    fullWidth={true}
                    onNewRequest={this.onNewRequest}
                    dataSource={this.state.comics.map((it) => it.title)}/>
                <List>
                    {
                        this.state.comics.map(function (item) {
                            return <Link key={item.source.id} to={`/comic/${item.source.id}`}>
                                <ComicCell
                                    item={item}
                                    title={item.title}
                                    comic_id={item.source.id}
                                    author={item.author}>
                                </ComicCell>
                            </Link>
                        })
                    }
                </List>
            </div>
        </MuiThemeProvider>
    }

    componentDidMount() {
        this.loadComics()
    }
}

export default AllComics;